"""Change TargetCode tables from varchar to int

Revision ID: d0c885df6cfa
Revises: 94e8e80b2fc8
Create Date: 2024-05-02 04:15:17.169023

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d0c885df6cfa"
down_revision: Union[str, None] = "94e8e80b2fc8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE target_code ALTER COLUMN func_scope SET DATA TYPE int4 USING (func_scope::int);"
    )
    op.execute(
        "ALTER TABLE target_code ALTER COLUMN class_scope SET DATA TYPE int4 USING (class_scope::int);"
    )


def downgrade() -> None:
    pass
