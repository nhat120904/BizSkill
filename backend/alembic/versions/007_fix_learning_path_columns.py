"""Fix learning_path columns length

Revision ID: 007_fix_learning_path_columns
Revises: 006_fix_watch_duration
Create Date: 2024-12-17 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_fix_learning_path_columns'
down_revision = '006_fix_watch_duration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase current_level and target_level column sizes
    op.alter_column('learning_paths', 'current_level',
                    type_=sa.String(200),
                    existing_type=sa.String(50))
    op.alter_column('learning_paths', 'target_level',
                    type_=sa.String(200),
                    existing_type=sa.String(50))


def downgrade() -> None:
    op.alter_column('learning_paths', 'current_level',
                    type_=sa.String(50),
                    existing_type=sa.String(200))
    op.alter_column('learning_paths', 'target_level',
                    type_=sa.String(50),
                    existing_type=sa.String(200))
