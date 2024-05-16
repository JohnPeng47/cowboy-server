from src.coverage.models import CoverageModel
from cowboy_lib.coverage import Coverage

from src.test_modules.models import TestModuleModel, TestModule

from pathlib import Path
from typing import List


def get_coverage_stats(tm: TestModule, cov: Coverage):
    """
    Calculate stats on what % of coverage is our baseline'd TestModule covering
    """
    total_covered = cov.covered
    tgt_covered = 0
    missing = cov.misses

    for chunk in tm.chunks:
        if Path(chunk.filepath) == cov.filename:
            tgt_covered += len(chunk.lines)

    score = get_score(tgt_covered, total_covered, missing)
    return score


def get_score(tgt_covered, total_covered, missing):
    return tgt_covered + missing / total_covered if total_covered else 0
