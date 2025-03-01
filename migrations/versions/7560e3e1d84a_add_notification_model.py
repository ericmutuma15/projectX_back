"""Add Notification model

Revision ID: 7560e3e1d84a
Revises: 0fa7559eeb6a
Create Date: 2025-02-27 14:04:37.666412

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7560e3e1d84a'
down_revision = '0fa7559eeb6a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('notification',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=255), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('notification')
    # ### end Alembic commands ###
