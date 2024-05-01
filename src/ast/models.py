from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean

from cowboy_lib.ast.code import ASTNode
from cowboy_lib.repo.source_repo import SourceRepo
from src.database.core import Base


class NodeModel(Base):
    """
    An AST node, either a class or a function, that holds a single or a group of unit tests
    """

    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    node_type = Column(String)
    testfilepath = Column(String)

    # start_line = Column(Integer)
    # end_line = Column(Integer)
    # lines = Column(String)
    # is_test = Column(Boolean)
    # scope_id = Column(Integer, ForeignKey("nodes.id"))
    # children = relationship(
    #     "NodeModel",
    #     backref=backref("parent", remote_side=[id]),
    #     cascade="all, delete-orphan",
    # )

    # # decorators = Column

    test_module_id = Column(Integer, ForeignKey("test_modules.id"))
    repo_id = Column(Integer, ForeignKey("repo_config.id"))

    # chunks = relationship("TargetCodeModel", backref="nodes")

    def to_astnode(self, source_repo: SourceRepo):
        return source_repo.find_node(self.name, self.testfilepath, self.node_type)

    @classmethod
    def from_astnode(cls, node: ASTNode) -> "NodeModel":
        return cls(
            name=node.name,
            node_type=node.node_type,
        )
