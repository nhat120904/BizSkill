"""Add created_at to segment_categories

Revision ID: 002_add_created_at
Revises: 001_initial
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_created_at'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add created_at column to segment_categories table
    op.add_column(
        'segment_categories',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_column('segment_categories', 'created_at')
