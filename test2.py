# import sys

# sys.path.append("/home/ubuntu/cowboy-server-good")

from cowboy_lib.repo import SourceRepo
from src.test_modules.service import get_all_tms

from src.database.core import engine

from sqlalchemy.orm import sessionmaker
from pathlib import Path


repo_path = "/home/ubuntu/cowboy-server-good/repos/test8/mbvyvqlp"
src_repo = SourceRepo(Path(repo_path))
Session = sessionmaker(bind=engine)
db_session = Session()

tms = get_all_tms(db_session=db_session, repo_id=9)
for tm in tms:
    print(tm.name)
    tm = tm.serialize(src_repo)
    if tm.chunks:
        print(tm.print_chunks())
