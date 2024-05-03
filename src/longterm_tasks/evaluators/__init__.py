from .eval_base import Evaluator

from .augment_parallel import AugmentParallelEvaluator
from .augment_additive import AugmentAdditiveEvaluator

from enum import Enum


class EvaluatorType(Enum):
    PARALLEL = "PARALLEL"
    ADDITIVE = "ADDITIVE"


AUGMENT_EVALS = {
    "PARALLEL": AugmentParallelEvaluator,
    "ADDITIVE": AugmentAdditiveEvaluator,
}
