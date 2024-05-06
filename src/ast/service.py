from cowboy_lib.ast.code import ASTNode
from cowboy_lib.test_modules.test_module import TestModule

from src.database.core import Session
from src.test_modules.models import TestModuleModel

from .models import NodeModel


def get_node(
    *, db_session: Session, node_name: str, repo_id: int, node_type: str, filepath: str
):
    return (
        db_session.query(NodeModel)
        .filter(
            NodeModel.name == node_name
            and NodeModel.repo_id == repo_id
            and NodeModel.node_type == node_type
            and NodeModel.testfilepath == filepath
        )
        .one_or_none()
    )


def create_node(
    *,
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

    print(
        "Node Created: ",
        node.name,
        node.node_type,
        node.repo_id,
        node.testfilepath,
        node.test_module_id,
    )

    db_session.add(node)
    db_session.commit()

    return node


def create_or_update_node(
    *, db_session: Session, repo_id: str, node: ASTNode, filepath: str
):
    old_node = get_node(
        db_session=db_session,
        node_name=node.name,
        repo_id=repo_id,
        node_type=node.node_type,
        filepath=filepath,
    )

    if old_node:
        # NOTE: there is actually no point in updating node right now
        # because none of the node attributes should change ..
        print("Node exists: ", node.name)
        # node_model = (
        #     db_session.query(NodeModel)
        #     .filter(
        #         NodeModel.name == node.name
        #         and NodeModel.repo_id == repo_id
        #         and NodeModel.node_type == node.node_type
        #         and NodeModel.testfilepath == filepath
        #     )
        #     .update(node)
        # )
        return old_node
    else:
        node_model = create_node(
            db_session=db_session, node=node, repo_id=repo_id, filepath=filepath
        )

    return node_model
