"""add new job type

Revision ID: 80b46bdbbc83
Revises: 1b37a9904f96
Create Date: 2020-07-08 02:51:30.694998

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '80b46bdbbc83'
down_revision = '1b37a9904f96'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TYPE scheduledjobtypes ADD VALUE \'PODCAST_RSS\'')


def downgrade():
    op.execute('ALTER TYPE scheduledjobtypes DROP VALUE \'PODCAST_RSS\'')

