from src.database.core import Session
from src.ast.models import NodeModel
from src.target_code.models import TargetCode, TargetCodeModel
from src.test_modules.models import TestModuleModel
from src.coverage.models import CoverageModel


def create_target_code(
    db_session: Session,
    tm_model: TestModuleModel,
    chunk: TargetCode,
    cov_model: CoverageModel,
    func_scope: NodeModel = None,
    class_scope: NodeModel = None,
):
    """Create a target code chunk for a test module."""

    target_code = TargetCodeModel(
        lines=chunk.lines,
        start=chunk.range[0],
        end=chunk.range[1],
        filepath=chunk.filepath,
        func_scope=func_scope,
        class_scope=class_scope,
        test_module_id=tm_model.id,
        coverage_id=cov_model.id,
    )

    db_session.add(target_code)
    db_session.commit()

    return target_code
