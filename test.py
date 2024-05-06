from cowboy_lib.repo.source_repo import SourceRepo
from src.test_modules.iter_tms import iter_test_modules
from pathlib import Path

s = SourceRepo(Path("repos/test2/upflwdnk"))
tms = iter_test_modules(s)
testing = []
for tm in tms[:4]:
    testing.append(tm)
    print(tm.name, tm.test_file.path)

print([t.name for t in testing])
