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
from src.local.db import get_repo, get_tm
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
@click.option("--keep", type=int, default=2,
              help="Number of test functions to keep per module")
@click.option("--delete", type=int, default=0,
              help="Number of test functions to delete per module")
@click.option("--num-tms", type=int, default=5,
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

    if selected_tms:
        filtered_tms = [tm for tm in test_modules if tm.name in selected_tms]
    else:
        filtered_tms = test_modules[::skip]
        filtered_tms = filtered_tms[1:len(filtered_tms)]
    
    handicapped = []
    processed_tms = 0
    for tm in filtered_tms:
        target_files, chunks = await get_tm_target_files(repo.repo_name, base_cov, src_repo, tm)
        tm.target_files = [Path(f) for f in target_files]
        tm.chunks = chunks

        try:
            # NEWTODO: not handling cases where there are multiple testfiles mapped to a TestModule
            testfile_fp, newfile_contents, deleted = await handicap_tm(
                dataset,
                repo.repo_name,
                tm,
                Path(repo.source_folder), 
                to_keep=keep, 
                to_delete=delete,
            )
            if testfile_fp and newfile_contents and deleted:
                handicapped.append((testfile_fp, newfile_contents, deleted))
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
