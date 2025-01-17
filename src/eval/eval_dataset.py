import dotenv
from typing import Dict, List
from braintrust import EvalAsync

from src.lib.coverage import TestCoverage

from src.local.augment_tests import extend_tests

dotenv.load_dotenv()

## Scoring functions
def score_coverage(output: Dict, expected: Dict):
    """
    Coverage improvement out of total possible expected coverage (sum of all coverage 
    from neutered tests)
    """
    name = output["name"]
    total_cov = TestCoverage.deserialize(expected)
    cov_added = TestCoverage.deserialize(output["cov_added"])

    for f in output["target_files"]:
        if f in [cov.filename for cov in total_cov.cov_list]:
            print(f"{name} has matching target_files : {f} !!!")
        
    score = total_cov.get_covered(cov_added)
    
    # print("COV EXPECTED:")
    # for cov_expected in total_cov.cov_list:
    #     print(cov_expected)

    # print("COV ADDED:")
    # for cov_add in cov_added.cov_list:
    #     print(cov_add)

    print(f"Cov added: {score} / {total_cov.total_cov.covered}")
    return score / total_cov.total_cov.covered

def score_improved_tests(output: Dict, expected: int):
    """
    Number of tests improved out of total possible expected tests
    """
    improved = output["improved"]
    no_improve = output["no_improve"]
    failed = output["failed"]

    return improved / (improved + no_improve + failed)

async def eval_dataset(repo_name: str,
                       tm_datalist: List[Dict],
                       experiment_name: str):
    """
    Evaluate the dataset locally
    """

    for dataset in tm_datalist:
        await extend_tests(dataset)

async def eval_dataset_braintrust(repo_name: str, 
                                  tm_datalist: List[Dict],
                                  experiment_name: str,
                                  project_name: str = ""):
    """
    Evaluate the dataset locally and save results to braintrust
    """    

    await EvalAsync(
        repo_name + project_name,
        tm_datalist,
        extend_tests,
        [score_coverage, score_improved_tests],
        experiment_name = experiment_name
    )