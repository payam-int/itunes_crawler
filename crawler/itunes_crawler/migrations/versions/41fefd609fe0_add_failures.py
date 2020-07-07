"""add failures

Revision ID: 41fefd609fe0
Revises: ebc465a962fd
Create Date: 2020-07-08 03:17:25.364127

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41fefd609fe0'
down_revision = 'ebc465a962fd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('scheduled_jobs', sa.Column('failures', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('scheduled_jobs', 'failures')
    # ### end Alembic commands ###