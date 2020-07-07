"""seed database

Revision ID: 7ef4e32726fa
Revises: 185ae507c9bb
Create Date: 2020-07-07 01:09:34.350682

"""
from alembic import op
# revision identifiers, used by Alembic.
from sqlalchemy import delete

from itunes_crawler.models2 import ScheduledJob, ScheduledJobTypes

revision = '7ef4e32726fa'
down_revision = '185ae507c9bb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO scheduled_jobs(type, id) VALUES('{type}', '{id}')".format(
        type=ScheduledJobTypes.TOP_LEVEL_CATEGORIES.value,
        id='1'))


def downgrade():
    op.execute(delete(ScheduledJob)
               .where(ScheduledJob.id == '1')
               .where(ScheduledJob.type == ScheduledJobTypes.TOP_LEVEL_CATEGORIES))
