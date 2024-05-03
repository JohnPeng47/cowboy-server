from .augment_strat import AugmentClassStrat
from .augment_with_ctxt_file import AugmentClassWithCtxtStrat
from .augment_base import AugmentTestStrategy
from .augment_with_missing import AugmentModuleMissing

from enum import Enum

AUGMENT_STRATS = {
    "VANILLA": AugmentClassStrat,
    "WITH_CTXT": AugmentClassWithCtxtStrat,
    "MODULE_MISSING": AugmentModuleMissing,
}


class AugmentStratType(Enum):
    VANILLA = "VANILLA"
    WITH_CTXT = "WITH_CTXT"
    MODULE_MISSING = "MODULE_MISSING"
