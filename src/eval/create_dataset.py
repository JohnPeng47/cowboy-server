import json
from typing import List, Tuple
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from braintrust import Dataset
from pydantic import BaseModel

from src.lib.test_modules import TestModule
from src.lib.ast import NodeType
from src.lib.coverage import TestCoverage

from src.llm import LLMModel, LMP
from src.config import TESTCONFIG_ROOT
from src.database.core import engine
from src.runner.local.run_test import run_test as run_test_local
from src.local.models import TestModuleEvalData, RemovedTest
from src.logger import buildtm_logger as log
from src.utils import red_text

class NoTestsToDelete(Exception):
    pass

class NoDiff(Exception):
    pass

# Create a session factory (similar to main.py)
Session = sessionmaker(bind=engine)

class TestConditions(BaseModel):
    conditions: List[str]

class ExtractTestConditions(LMP):
    prompt = """
Given the following source files:
{source_files}

And the test cases that cover these files:
{test_cases}

Extract a set of conditions/states that the tests are checking for in the sourcefile(s). 
These test conditions should reflect both implicit and explicit assertions made in the test case
Now, extract the set of test conditions
"""
    response_format = TestConditions


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

async def handicap_tm(
    dataset: Dataset,
    targeted_srcfiles: List[str],
    repo_name: str,
    tm: TestModule, 
    repo_path: Path, 
    to_keep, 
    to_delete=0,
    ask_confirm=True,
) -> Tuple[TestModuleEvalData, str, int]:
    """
    Iterate TestModules and delete tests from each according to to_keep/to_delete. 
    Process up to max_tm test modules. Writes summary of deleted tests to disk
    """
    with open(TESTCONFIG_ROOT / f"{repo_name}.json", "r") as f:
        repo_config = json.loads(f.read())        

    base_path = repo_path
    total_deleted = 0
    num_to_del = num_delete(tm, to_keep=to_keep, to_delete=to_delete)

    log.info(f"Deleting {num_to_del} tests from {tm.name}")

    # we take the module coverage before and after the unit tests have been rmeoved
    # to calcuate the difference in coverage
    cov_diff = TestCoverage([], isdiff=True)
    removed_tests = []
    modcov_before = await run_test_local(repo_name, None, include_tests=tm, use_cache=False)
    for func in tm.tests[:num_to_del]:
        tm.test_file.delete(
            func.name, node_type=NodeType.Function
        )
        modcov_notest = await run_test_local(
            repo_name, None, 
            include_tests=tm,
            exclude_tests=[(func, tm.test_file.path)], 
            use_cache=False
        )
        test_cov = modcov_before.get_coverage() - modcov_notest.get_coverage()     
        targeted_cov = TestCoverage([], isdiff=True)
        for cov in test_cov.cov_list:
            if cov.filename in targeted_srcfiles:
                targeted_cov += cov
                cov_diff += cov

        removed_tests.append(RemovedTest(name=func.name, content=func.to_code(), cov=targeted_cov))
        total_deleted += 1

    # write deleted test_file contents to disk and measure coverage diff
    handicap_testfile = tm.test_file.to_code()
    with open(base_path / tm.test_file.path, "w", encoding="utf-8") as f:
        f.write(handicap_testfile)
        
    if cov_diff.total_cov.covered == 0:
        log.info(red_text(f"No coverage after removing {total_deleted} tests"))
    
        # so we dont count this one in the outer loop
        raise Exception("No coverage after removing tests")
    
    else:
        row = TestModuleEvalData(
            name=tm.name,
            file_content=handicap_testfile,
            repo_config=repo_config,
            removed_tests=removed_tests,
            tags=[tm.name],
            expected=cov_diff
        )

        # NEWTODO: upload data to braintrust
        # dataset.update(
        #     tm.name,
        #     TestModuleRow(
        #         tm=tm,
        #         base_cov=base_cov,
        #         file_content=file_contents,
        #         module_cov=diff_cov,
        #         repo_config=repo_config,
        #         expected=diff_cov.total_cov.covered
        #     ).to_json(),
        #     tags=[tm.name]
        # )

        log.info(f"Diff coverage: {cov_diff.total_cov.covered}")
        log.info(f"Updating dataset with: {tm.name}")

        return row, handicap_testfile, total_deleted
        