from typing import List, Optional
from pathlib import Path
from collections import defaultdict

from src.lib.repo import SourceRepo
from src.lib.test_modules import TestModule
from src.lib.ast import NodeType

from src.test_modules.iter_tms import iter_test_modules
from src.database.core import engine

def num_delete(tm: TestModule, to_keep: int = 1, to_delete: int = 1) -> int:
    if to_keep and to_delete:
        raise Exception("Cannot have both values > 0")

    # always leave at least one test
    if to_keep:
        num_to_del = max(0, len(tm.tests) - to_keep)
        return num_to_del
    elif to_delete:
        num_to_del = min(len(tm.tests) - 1, to_delete)
        return num_to_del
    else:
        raise Exception("Must provide either to_keep or to_delete value")

def neuter_tests(
    test_modules: List[TestModule], 
    src_repo: SourceRepo, 
    to_keep, 
    to_delete=0,
    max_total_delete=None,
    out_repo: Optional[Path] = None
):
    """
    Iterate TestModules and delete tests from each according to to_keep/to_delete. Stop
    when max_total_delete is reached. Writes summary of deleted tests to disk
    """
    total_deleted = 0
    failed_mod = 0
    deleted_per_module = defaultdict(int)
    
    for test_file in src_repo.test_files:
        for tm in [tm for tm in test_modules if tm.test_file == test_file]:
            # og_bytes = len(open(src_repo.repo_path / test_file.path, "r", "utf-8").read())
            try:
                tm_deleted = 0
                to_exclude = []
                num_to_del = num_delete(tm, to_keep=to_keep, to_delete=to_delete)
                
                # Check if we would exceed max_total_delete
                if max_total_delete and total_deleted + num_to_del > max_total_delete:
                    num_to_del = max(0, max_total_delete - total_deleted)
                    if num_to_del == 0:
                        break

                for func in tm.tests[:num_to_del]:
                    to_exclude.append((func, tm.test_file.path))
                    src_repo.find_file(tm.path).delete(
                        func.name, node_type=NodeType.Function
                    )
                    deleted_per_module[tm.name] += 1
                    total_deleted += 1
                    tm_deleted += 1
                    
                    # Check if we've hit the max after each deletion
                    if max_total_delete and total_deleted >= max_total_delete:
                        break

                print("Deleted", tm_deleted, "tests from", tm.name)
                
            except Exception as e:
                failed_mod += 1

        base_path = out_repo if out_repo else src_repo.repo_path
        output_path = base_path / test_file.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(src_repo.find_file(test_file.path).to_code())

        new_bytes = len(src_repo.find_file(test_file.path).to_code())

    # Print summary of affected modules
    summary = "\nSummary of affected modules:\n"
    for module, count in deleted_per_module.items():
        summary += f"  {module}: {count} tests deleted\n"
    
    summary += f"\nTotal tests deleted: {total_deleted}\n"
    summary += f"Total failed: {failed_mod}"
    with open(base_path / "neuter_summary.txt", "w") as f:
        f.write(summary)
    

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Neuter a repository by removing test functions while keeping a specified number"
    )
    parser.add_argument(
        "repo_path",
        type=str,
        help="Path to the repository to neuter"
    )
    parser.add_argument(
        "--out-repo",
        type=str,
        help="Optional path to output neutered repository (defaults to modifying original)",
        default=None
    )
    parser.add_argument(
        "--keep",
        type=int,
        help="Number of test functions to keep per module (default: 2)",
        default=2
    )
    parser.add_argument(
        "--delete",
        type=int,
        help="Number of test functions to delete per module (default: 0, meaning keep specified number)",
        default=0
    )
    parser.add_argument(
        "--max-delete",
        type=int,
        help="Maximum total number of tests to delete across all modules",
        default=None
    )

    args = parser.parse_args()
    repo = Path(args.repo_path)
    if not repo.exists():
        parser.error("Repository path does not exist")

    out_repo = Path(args.out_repo) if args.out_repo else None
    src_repo = SourceRepo(repo)
    test_modules = iter_test_modules(src_repo)

    neuter_tests(
        test_modules, 
        src_repo, 
        to_keep=args.keep, 
        to_delete=args.delete,
        max_total_delete=args.max_delete,
        out_repo=out_repo
    )
