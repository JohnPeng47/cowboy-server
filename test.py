# import sys

# sys.path.append("/home/ubuntu/cowboy-server-good")

from cowboy_lib.repo import SourceRepo
from src.test_modules.service import get_tm_by_name, get_all_tms

from src.database.core import engine

from sqlalchemy.orm import sessionmaker
from pathlib import Path


repo_path = "/home/ubuntu/cowboy-server-good/repos/test2/qrjmnlxt"
src_repo = SourceRepo(Path(repo_path))
Session = sessionmaker(bind=engine)
db_session = Session()


# tm_model = get_tm_by_name(db_session=db_session, repo_id=17, tm_name="TestWoodpecker")
# tm = tm_model.serialize(src_repo)

tm_models = get_all_tms(db_session=db_session, repo_id=17)
tm_models = sorted(tm_models, key=lambda tm: tm.agg_score(src_repo), reverse=True)

for tm in tm_models:
    print(tm.name, tm.agg_score(src_repo))
