from typing import List, Any, Optional, Dict

from sqlalchemy import Column, Integer, String, JSON, ForeignKey

from src.models import CowboyBase
from src.database.core import Base


# TODO: remove fields we dont need
class RepoConfig(Base):
    """
    Stores configuration for a repository
    """

    __tablename__ = "repo_config"

    id = Column(Integer, primary_key=True)
    repo_name = Column(String)
    url = Column(String)
    forked_url = Column(String)
    cloned_folders = Column(String)  # Handling list as comma-separated string
    source_folder = Column(String)

    # keep this argument fluid, may change
    python_conf = Column(JSON)
    user_id = Column(Integer, ForeignKey("cowboy_user.id"))

    def __init__(
        self,
        repo_name,
        url,
        forked_url,
        cloned_folders,
        source_folder,
        python_conf,
        user_id,
    ):
        self.repo_name = repo_name
        self.url = url
        self.forked_url = forked_url
        self.cloned_folders = ",".join(cloned_folders)
        self.source_folder = source_folder
        self.python_conf = python_conf
        self.user_id = user_id

    def get_cloned_folders(self):
        return self.cloned_folders.split(",")

    def as_dict(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "forked_url": self.forked_url,
            "cloned_folders": self.get_cloned_folders(),
            "source_folder": self.source_folder,
            "python_conf": self.python_conf,
            "user_id": self.user_id,
        }


# Pydantic models...
class PythonConf(CowboyBase):
    cov_folders: List[str]
    test_folder: str
    interp: str
    pythonpath: str

    def get(self, __name: str, default: Any = None) -> Any:
        return self.dict().get(__name, default)


class RepoConfigBase(CowboyBase):
    repo_name: str
    url: str
    forked_url: str
    # cloned_folders: List[str]
    source_folder: str
    python_conf: Dict[str, Any]


class RepoConfigGet(RepoConfigBase):
    pass


class RepoConfigCreate(RepoConfigBase):
    repo_name: str


class RepoConfigList(CowboyBase):
    repo_list: List[RepoConfigBase]


# class RepoConfigDelete(BaseModel):
#     repo_name: str
