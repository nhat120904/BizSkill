"""add cloudinary fields to segments

Revision ID: 003
Revises: 002_add_created_at
Create Date: 2024-12-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_cloudinary_fields'
down_revision = '002_add_created_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Cloudinary fields to segments table
    op.add_column('segments', sa.Column('cloudinary_url', sa.String(500), nullable=True))
    op.add_column('segments', sa.Column('cloudinary_public_id', sa.String(200), nullable=True))
    op.add_column('segments', sa.Column('cloudinary_thumbnail_url', sa.String(500), nullable=True))
    op.add_column('segments', sa.Column('clip_status', sa.String(20), nullable=True, server_default='pending'))
    op.add_column('segments', sa.Column('clip_processed_at', sa.DateTime(), nullable=True))
    
    # Create index on clip_status for filtering
    op.create_index('ix_segments_clip_status', 'segments', ['clip_status'])


def downgrade() -> None:
    op.drop_index('ix_segments_clip_status', table_name='segments')
    op.drop_column('segments', 'clip_processed_at')
    op.drop_column('segments', 'clip_status')
    op.drop_column('segments', 'cloudinary_thumbnail_url')
    op.drop_column('segments', 'cloudinary_public_id')
    op.drop_column('segments', 'cloudinary_url')
