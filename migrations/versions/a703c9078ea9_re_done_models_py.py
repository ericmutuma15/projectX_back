"""re-done models.py

Revision ID: a703c9078ea9
Revises: 2262273a42d7
Create Date: 2024-12-02 11:15:37.600316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a703c9078ea9'
down_revision = '2262273a42d7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password', sa.String(length=200), nullable=False))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.String(length=100),
               existing_nullable=False)
        batch_op.alter_column('email',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.String(length=100),
               existing_nullable=False)
        batch_op.drop_column('created_at')
        batch_op.drop_column('google_id')
        batch_op.drop_column('profile_picture')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column('google_id', sa.VARCHAR(length=255), nullable=False))
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=True))
        batch_op.alter_column('email',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
        batch_op.alter_column('name',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
        batch_op.drop_column('password')

    # ### end Alembic commands ###
