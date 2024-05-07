from cowboy_lib.repo.source_repo import SourceRepo
from src.test_modules.iter_tms import iter_test_modules
from src.test_modules.models import TestModuleModel
from pathlib import Path

from src.database.core import engine
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()
tm = (
    session.query(TestModuleModel)
    .filter(TestModuleModel.name == "TestWoodpecker")
    .filter(TestModuleModel.repo_id == 38)
    .one_or_none()
)

print(tm.target_chunks)
# s = SourceRepo(Path("repos/test2/upflwdnk"))
# tms = iter_test_modules(s)
# testing = []
# for tm in tms:
#     if tm.name != "TestWoodpecker":
#         continue

#     print(tm.name, tm.test_file.path)
