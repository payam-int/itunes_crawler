"""add some tables

Revision ID: 1b37a9904f96
Revises: 15ddff36f0bf
Create Date: 2020-07-07 22:44:56.075028

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b37a9904f96'
down_revision = '15ddff36f0bf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('itunes_podcast_lookup',
                    sa.Column('itunes_id', sa.String(), nullable=False),
                    sa.Column('itunes_lookup', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('itunes_id')
                    )
    op.create_table('itunes_podcast_rss',
                    sa.Column('itunes_id', sa.String(), nullable=False),
                    sa.Column('rss', sa.String(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('itunes_id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('itunes_podcast_rss')
    op.drop_table('itunes_podcast_lookup')
    # ### end Alembic commands ###
