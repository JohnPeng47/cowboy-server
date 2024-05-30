from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from src.database.core import Base


# TODO: make this track module level stats later
class RepoStats(Base):
    """
    Tracks repo level stats
    """

    __tablename__ = "repo_stats"

    id = Column(Integer, primary_key=True)
    total_tests = Column(Integer, default=0)
    accepted_tests = Column(Integer, default=0)
    rejected_tests = Column(Integer, default=0)

    repo_id = Column(Integer, ForeignKey("repo_config.id", ondelete="CASCADE"))
