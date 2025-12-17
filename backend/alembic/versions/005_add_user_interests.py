"""Add user_interests table

Revision ID: 005_add_user_interests
Revises: 004_add_learning_paths
Create Date: 2024-12-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_user_interests'
down_revision = '004_add_learning_paths'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_interests table
    op.create_table(
        'user_interests',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_user_interests_user_id', 'user_interests', ['user_id'])
    op.create_index('ix_user_interests_category_id', 'user_interests', ['category_id'])


def downgrade() -> None:
    op.drop_index('ix_user_interests_category_id', table_name='user_interests')
    op.drop_index('ix_user_interests_user_id', table_name='user_interests')
    op.drop_table('user_interests')
