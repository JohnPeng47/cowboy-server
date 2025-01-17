import sys
import asyncio
import click
from pathlib import Path
from typing import List, Tuple
from braintrust import init_dataset
from functools import wraps
import git

from src.lib.test_modules import TestModule
from src.lib.repo import SourceRepo

from src.runner.local.run_test import run_test
from src.test_modules.iter_tms import iter_test_modules
from src.config import BT_PROJECT, BRAINTRUST_API_KEY
from src.eval.eval_dataset import eval_dataset, eval_dataset_braintrust
from src.eval.create_dataset import handicap_tm, NoTestsToDelete, NoDiff
from src.local.db import get_repo, get_tm, persist_tm
from src.local.models import TestResults, TestModuleData, read_rows
from src.local.tgt_coverage import get_tm_target_files
from src.local.apply import (
    validate, 
    print_test_summary, 
    TestApplyError,
    apply_tests
)
from src.utils import confirm_action, red_text

from src.logger import buildtm_logger


def parse_list(ctx, param, value):
    if not value:
        return []
    return [x.strip() for x in value.split(",")]

def coro(f):
    """Decorator to run async functions using click"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@click.group()
def cli():
    """CLI tool for test evaluation and repository neutering operations."""
    pass

@cli.command()
@click.argument("repo_name", type=str)
@click.option("--num-tms", type=int, default=-1, 
              help="Number of records to evaluate (0 for all)")
@click.option("--selected-tms", 
              type=click.STRING, 
              callback=parse_list,
              default="",
              help="Comma-separated list of TestModules to evaluate (e.g. 'module1,module2')")
@click.option("--list-tms", is_flag=True, default=False,)
@click.option("--strat", type=str, default="WITH_CTXT",
              help="Strategy for test generation")
@click.option("--evaluator", type=str, default="ADDITIVE",
              help="Evaluator type")
@click.option("--model", type=str, default="gpt-4o")
@click.option("--n-times", type=int, default=2,
              help="Number of times to generate tests")
@click.option("--braintrust", is_flag=True, default=False,
              help="Whether to use Braintrust for evaluation")
@click.option("--project-name", type=str, default="",
              help="Braintrust project name")
@coro
async def evaluate(repo_name: str,
                   num_tms: int, 
                   list_tms: bool,
                   selected_tms: List[str],
                   strat: str, 
                   evaluator: str, 
                   n_times: int, 
                   model: str, 
                   braintrust: bool,
                   project_name: str):
    """Evaluate test augmentation on datasets."""
    if list_tms:
        read_rows(repo_name, braintrust, list_tms=True)
        sys.exit()
        
    if selected_tms and num_tms > 0:
        raise ValueError("Cannot provide both selected-tms and num-tms")
    
    if selected_tms:
        tm_datalist = read_rows(repo_name, braintrust, selected_tms=selected_tms)
    elif num_tms != -1:
        tm_datalist = read_rows(repo_name, braintrust, limit=num_tms)
    else:
        raise ValueError("Must provide either selected-tms or num-tms argument. If you want to run on all tests, use --num-tms BIG_NUMBER")

    src_covered_datalist = []
    for datum in tm_datalist:
        if get_tm(repo_name, datum.name).targeted_files():
            src_covered_datalist.append(datum)
        else:
            print(red_text(f"{datum.name} is not covered"))

    # convert to braintrust
    if braintrust:
        dataset = [datum.to_json_braintrust() for datum in src_covered_datalist]
        tm_names = [d["input"]["name"] for d in dataset]
        for d in dataset:
            d["input"].update(
                {
                    "strat": strat,
                    "evaluator": evaluator,
                    "n_times": n_times,
                    "model": model
                }
            )

    else:
        dataset = [datum.to_json() for datum in src_covered_datalist]
        tm_names = [d["name"] for d in dataset]
        for d in dataset:
            d.update(
                {
                    "strat": strat,
                    "evaluator": evaluator,
                    "n_times": n_times,
                    "model": model
                }
            )

    print("Evaluating TestModules => ", tm_names)

    experiment_name = f"{repo_name}::{model}::{strat}::{evaluator}::{n_times}_n_times"
    if braintrust:
        await eval_dataset_braintrust(
            repo_name, 
            dataset,
            experiment_name,
            project_name=project_name
        )
    else:
        await eval_dataset(
            repo_name, 
            dataset,
            experiment_name,
        )

@cli.command()
@click.argument("repo_name", type=str)
@click.option("--keep", type=int, default=2,
              help="Number of test functions to keep per module")
@click.option("--delete", type=int, default=0,
              help="Number of test functions to delete per module")
@click.option("--num-tms", type=int, default=None,
              help="Maximum number of test modules to process")
@click.option("--selected-tms", 
              type=click.STRING, 
              callback=parse_list,
              default="",
              help="Comma-separated list of TestModules to evaluate (e.g. 'module1,module2')")
@click.option("--skip", type=int, default=1,
              help="Num to skip while iterating")
@coro
async def setup_eval_repo(repo_name: str, 
                              keep: int, 
                              delete: int,
                              num_tms: int,
                              skip: int,
                              selected_tms: List[str]):
    """Neuter a repository by removing test functions."""
    repo = get_repo(repo_name)
    base_cov = await run_test(repo.repo_name, None)
    base_cov = base_cov.get_coverage()
    
    dataset = init_dataset(
        name=repo.repo_name, 
        project=BT_PROJECT, 
        api_key=BRAINTRUST_API_KEY
    )
    src_repo = SourceRepo(Path(repo.source_folder))
    test_modules = iter_test_modules(src_repo)

    click.echo(f"Creating {num_tms}/{len(test_modules)} datasets")
    click.echo(f"Set \"--max-tm\" to change number of datasets to create")

    if not num_tms:
        num_tms = 1000000 # large number

    if selected_tms:
        filtered_tms = [tm for tm in test_modules if tm.name in selected_tms]
    else:
        filtered_tms = test_modules[::skip]
    
    handicapped = []
    processed_tms = 0
    for tm in filtered_tms:
        try:
            target_files, chunks = await get_tm_target_files(repo.repo_name, base_cov, src_repo, tm)
            tm.target_files = [Path(f) for f in target_files]
            tm.chunks = chunks

            targeted_srcfiles = set(tm.get_targeted_files()).intersection(set(tm.get_targeted_files_from_chunks()))
            targeted_srcfiles = [str(fp) for fp in targeted_srcfiles]

            print(tm.get_targeted_files())
            print(tm.get_targeted_files_from_chunks())
            print(targeted_srcfiles)

            # NEWTODO: not handling cases where there are multiple testfiles mapped to a TestModule
            tm_dataset, newfile_contents, deleted = await handicap_tm(
                dataset,
                targeted_srcfiles,
                repo.repo_name,
                tm,
                Path(repo.source_folder), 
                to_keep=keep, 
                to_delete=delete,
            )
            persist_tm(tm_dataset, tm)

            if tm.test_file.path and newfile_contents and deleted:
                handicapped.append((tm.test_file.path, newfile_contents, deleted))
                processed_tms += 1
                if num_tms and processed_tms == num_tms:
                    break

        except (NoTestsToDelete, NoDiff):
            print(red_text(f"Skipping {tm.name} due to no diff or no tests to delete"))
            continue

    # NOTE: need to do this here or else subsequent calls to run_testsuite in handicap_tm will reset
    # the repo commit hash
    commit_msg = ""
    for fp, content, deleted in handicapped:
        with open(repo.source_folder / fp, "w", encoding="utf-8") as f:
            f.write(content)

        commit_msg += f"Deleted {deleted} tests from {fp}\n"

    # create a new commit for all of the changes
    git_repo = git.Repo(repo.source_folder)
    git_repo.git.add(".")
    git_repo.index.commit(commit_msg)

    print("Commited with message: ", commit_msg)


@cli.command()
@click.argument("repo_name", type=str)
@click.option("--num-tms", type=int, default=5,
              help="Maximum number of test modules to process")
@click.option("--skip", type=int, default=1,
              help="Num to skip while iterating")
@click.option("--selected-tms", 
              type=click.STRING, 
              callback=parse_list,
              default="",
              help="Comma-separated list of TestModules to evaluate (e.g. 'module1,module2')")
@coro
async def setup_repo(repo_name: str, 
                     num_tms: int,
                     skip: int,
                     selected_tms: List[str]) -> Tuple[List[TestModule], List[TestModuleData]]:
    """Setup a repo for local test augmentation"""
    repo = get_repo(repo_name, ret_json=True)
    base_cov = await run_test(repo["repo_name"], None, use_cache=True, delete_last=True)
    base_cov = base_cov.get_coverage()
    
    src_repo = SourceRepo(Path(repo["source_folder"]))
    test_modules = iter_test_modules(src_repo)

    click.echo(f"Creating {num_tms}/{len(test_modules)} datasets")
    click.echo(f"Set \"--max-tm\" to change number of datasets to create")

    if selected_tms:
        filtered_tms = [tm for tm in test_modules if tm.name in selected_tms]
    else:
        filtered_tms = test_modules[::skip]
        filtered_tms = filtered_tms[1:num_tms]
    
    for tm in filtered_tms:
        chunks = await enrich_tm_with_tgt_coverage(repo["repo_name"], src_repo, base_cov, tm)
        tm.chunks = chunks

        tm_data = TestModuleData(
            name=tm.name,
            file_content=tm.test_file.to_code(),
            repo_config=repo,
        )
        tm_data.persist(tm)

@cli.command()
@click.argument("output_path", type=click.Path(exists=True, path_type=Path))
@coro
async def apply(output_path: Path):
    """Apply generated tests from output files to target files."""
    
    test_cases_str = ""
    non_empty = []
    files = [output_path] if output_path.is_file() else list(output_path.rglob("*.yml"))
    for file in files:
        try:
            test_results = TestResults.from_file(file)
            validate(test_results)

            test_cases_str += print_test_summary(file, test_results)
            non_empty.append(test_results)

        except TestApplyError as e:
            click.echo(f"TestResult validation error: {e} => Skipping {file}", err=True)
            continue

    confirm = confirm_action(test_cases_str)
    if not confirm:
        sys.exit(1)

    for test_results in non_empty:
        apply_tests(test_results)

def main():
    """Entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()