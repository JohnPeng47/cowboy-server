from pydantic import BaseModel
from typing import List, Any, Optional

from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declarative_base

# Define the base class
Base = declarative_base()


class RepoConfig(Base):
    __tablename__ = "repo_config"

    id = Column(Integer, primary_key=True)
    repo_name = Column(String)
    url = Column(String)
    forked_url = Column(String)
    cloned_folders = Column(String)  # Handling list as comma-separated string
    source_folder = Column(String)
    python_conf = Column(JSON)  # Storing PythonConf as a JSON field

    def __init__(
        self, repo_name, url, forked_url, cloned_folders, source_folder, python_conf
    ):
        self.repo_name = repo_name
        self.url = url
        self.forked_url = forked_url
        self.cloned_folders = ",".join(cloned_folders)
        self.source_folder = source_folder
        self.python_conf = python_conf

    def get_cloned_folders(self):
        return self.cloned_folders.split(",")


class PythonConf(BaseModel):
    cov_folders: List[str]
    test_folder: str
    interp: str
    pythonpath: str

    def get(self, __name: str, default: Any = None) -> Any:
        return self.dict().get(__name, default)
