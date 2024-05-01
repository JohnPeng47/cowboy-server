"""Added testmodules

Revision ID: b4b0ffad026d
Revises: 5a9b1afb76e3
Create Date: 2024-04-30 22:08:23.733495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4b0ffad026d'
down_revision: Union[str, None] = '5a9b1afb76e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('target_code',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('range', sa.String(), nullable=True),
    sa.Column('lines', sa.String(), nullable=True),
    sa.Column('filepath', sa.String(), nullable=True),
    sa.Column('func_scope', sa.String(), nullable=True),
    sa.Column('class_scope', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('test_modules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('testfilepath', sa.String(), nullable=True),
    sa.Column('commit_sha', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('nodes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('node_type', sa.String(), nullable=True),
    sa.Column('test_module_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['test_module_id'], ['test_modules.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('nodes')
    op.drop_table('test_modules')
    op.drop_table('target_code')
    # ### end Alembic commands ###
