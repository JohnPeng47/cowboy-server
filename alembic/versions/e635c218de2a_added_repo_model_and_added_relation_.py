"""Added repo model and added relation from user to many repos

Revision ID: 84e9f0d53973
Revises: 4b2308ac52fa
Create Date: 2024-04-23 21:30:25.896998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84e9f0d53973'
down_revision: Union[str, None] = '4b2308ac52fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
