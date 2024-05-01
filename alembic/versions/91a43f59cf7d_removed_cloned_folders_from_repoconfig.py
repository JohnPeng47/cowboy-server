"""removed cloned_folders from RepoConfig

Revision ID: 91a43f59cf7d
Revises: baca7f3acb5c
Create Date: 2024-04-30 23:40:02.904914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91a43f59cf7d'
down_revision: Union[str, None] = 'baca7f3acb5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('repo_config', 'cloned_folders')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('repo_config', sa.Column('cloned_folders', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###