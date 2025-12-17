"""Fix watch_duration column name

Revision ID: 006_fix_watch_duration
Revises: 005_add_user_interests
Create Date: 2024-12-17 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_fix_watch_duration'
down_revision = '005_add_user_interests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column watch_duration to watch_duration_seconds
    op.alter_column('user_history', 'watch_duration', new_column_name='watch_duration_seconds')


def downgrade() -> None:
    op.alter_column('user_history', 'watch_duration_seconds', new_column_name='watch_duration')
