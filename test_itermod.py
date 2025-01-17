from pathlib import Path

from src.test_modules.iter_tms import iter_test_modules
from src.local.db import persist_tm

from src.lib.repo.source_repo import SourceRepo

src_repo = SourceRepo(Path("/home/ubuntu/cowboy-data/test_repo"))
tms = iter_test_modules(src_repo)
for t in tms:
    persist_tm("testrepo", t)