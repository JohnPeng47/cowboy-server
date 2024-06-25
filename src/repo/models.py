from cowboy_lib.coverage import TestCoverage

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import Field

from src.models import CowboyBase
from src.database.core import Base
from src.config import Language

from typing import List, Any, Dict, Optional


class RepoConfig(Base):
    """
    Stores configuration for a repository
    """

    __tablename__ = "repo_config"

    id = Column(Integer, primary_key=True)
    repo_name = Column(String)
    url = Column(String)
    source_folder = Column(String)
    cloned_folders = Column(String)
    # git remote and git main branch (to merge into)
    remote = Column(String)
    main = Column(String)
    language = Column(String)

    # keep this argument fluid, may change
    python_conf = Column(JSON)
    user_id = Column(Integer, ForeignKey("cowboy_user.id"))
    is_experiment = Column(Boolean)

    # relations
    test_modules = relationship(
        "TestModuleModel", backref="repo_config", cascade="all, delete-orphan"
    )
    nodes = relationship(
        "NodeModel", backref="repo_config", cascade="all, delete-orphan"
    )
    cov_list = relationship(
        "CoverageModel", backref="repo_config", cascade="all, delete-orphan"
    )
    stats = relationship("RepoStats", uselist=False, cascade="all, delete-orphan")

    def __init__(
        self,
        repo_name,
        url,
        source_folder,
        cloned_folders,
        python_conf,
        user_id,
        remote,  # origin
        main,
        language,
        is_experiment=False,
    ):
        self.repo_name = repo_name
        self.url = url
        self.source_folder = source_folder
        self.cloned_folders = ",".join(cloned_folders)
        self.python_conf = python_conf
        self.user_id = user_id
        self.remote = remote
        self.main = main
        self.language = language
        self.is_experiment = is_experiment

    def to_dict(self):
        return {
            "repo_name": self.repo_name,
            "url": self.url,
            "source_folder": self.source_folder,
            "cloned_folders": self.cloned_folders.split(","),
            "python_conf": self.python_conf,
            "user_id": self.user_id,
            "remote": self.remote,
            "main": self.main,
            "language": self.language,
            "is_experiment": self.is_experiment,
        }

    @property
    def base_cov(self) -> TestCoverage:
        return TestCoverage([cov.deserialize() for cov in self.cov_list])


class LangConf(CowboyBase):
    """
    Holds the language/framework specific settings
    for a repo
    """

    # currently I expect only an interpreter/compiler path that points
    # to the runtime for the targeted repo
    interp: str


class PythonConf(LangConf):
    language: str = "python"
    cov_folders: List[str]
    test_folder: str
    interp: str
    pythonpath: str

    def get(self, __name: str, default: Any = None) -> Any:
        return self.dict().get(__name, default)


class RepoConfigBase(CowboyBase):
    repo_name: str
    url: str
    source_folder: str
    cloned_folders: List[str]
    python_conf: PythonConf

    language: Optional[Language]
    is_experiment: Optional[bool]
    main: Optional[str]
    remote: Optional[str]


class RepoConfigGet(RepoConfigBase):
    pass


class RepoConfigCreate(RepoConfigBase):
    repo_name: str


class RepoConfigList(CowboyBase):
    repo_list: List[RepoConfigBase]


# class RepoConfigDelete(BaseModel):
#     repo_name: str
