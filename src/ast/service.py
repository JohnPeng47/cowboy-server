from cowboy_lib.ast.code import ASTNode
from cowboy_lib.test_modules.test_module import TestModule

from src.database.core import Session
from src.test_modules.models import TestModuleModel

from .models import NodeModel


def get_node(*, db_session: Session, node_name: str, repo_id: int, node_type: str):

    return (
        db_session.query(NodeModel)
        .filter(
            NodeModel.name == node_name
            and NodeModel.repo_id == repo_id
            and NodeModel.node_type == node_type
        )
        .one_or_none()
    )


def create_node(
    db_session: Session,
    node: ASTNode,
    repo_id: int,
    filepath: str,
    test_module_id: str = None,
):
    node = NodeModel(
        name=node.name,
        node_type=node.node_type.value,
        repo_id=repo_id,
        test_module_id=test_module_id,
        testfilepath=filepath,
    )

    db_session.add(node)
    db_session.commit()

    return node
