from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from cowboy_lib.ast.code import ASTNode
from src.database.core import Base


class NodeModel(Base):
    """
    An AST node, either a class or a function, that holds a single or a group of unit tests
    """

    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    node_type = Column(String)

    test_module_id = Column(Integer, ForeignKey("test_modules.id"))

    # chunks = relationship("TargetCodeModel", backref="nodes")

    def to_astnode(self):
        return ASTNode(name=self.name, type=self.node_type)

    @classmethod
    def from_astnode(cls, node: ASTNode) -> "NodeModel":
        return cls(
            name=node.name,
            node_type=node.node_type,
        )
