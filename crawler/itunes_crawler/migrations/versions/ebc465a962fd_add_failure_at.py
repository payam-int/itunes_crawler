"""add failure at

Revision ID: ebc465a962fd
Revises: 80b46bdbbc83
Create Date: 2020-07-08 03:06:44.193779

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ebc465a962fd'
down_revision = '80b46bdbbc83'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('scheduled_jobs', sa.Column('failure_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('scheduled_jobs', 'failure_at')
    # ### end Alembic commands ###
