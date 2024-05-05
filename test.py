from cowboy_lib.repo.source_repo import SourceRepo
from src.test_modules.iter_tms import iter_test_modules
from pathlib import Path

s = SourceRepo(Path("repos/codecov-cli-neuteured/xsmjhoph"))
tms = iter_test_modules(s)
for tm in tms:
    print(tm.name)
