from .models import AugmentTestResult

from collections import defaultdict
from typing import List


def gen_commit_msg(test_results: List[AugmentTestResult]):
    summary = defaultdict(int)
    for tr in test_results:
        summary[tr.testfile] += 1

    return f"COWBOY generated {','.join([f"{f}: {tests}\n" for f, tests in summary.items()])}"
