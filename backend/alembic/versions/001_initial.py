"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('youtube_channel_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('custom_url', sa.String(100), nullable=True),
        sa.Column('subscriber_count', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('youtube_id', sa.String(20), unique=True, nullable=False),
        sa.Column('channel_id', sa.String(36), sa.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_title', sa.String(500), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.BigInteger, default=0),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('transcript', sa.Text, nullable=True),
        sa.Column('transcript_segments', postgresql.JSONB, nullable=True),
        sa.Column('processing_error', sa.Text, nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_videos_youtube_id', 'videos', ['youtube_id'], unique=True)
    op.create_index('ix_videos_channel_id', 'videos', ['channel_id'])
    op.create_index('ix_videos_status', 'videos', ['status'])

    # Create segments table
    op.create_table(
        'segments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('video_id', sa.String(36), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('generated_title', sa.String(300), nullable=True),
        sa.Column('summary_text', sa.Text, nullable=True),
        sa.Column('key_takeaways', postgresql.JSONB, nullable=True),
        sa.Column('transcript_chunk', sa.Text, nullable=True),
        sa.Column('start_time', sa.Float, nullable=False),
        sa.Column('end_time', sa.Float, nullable=False),
        sa.Column('relevance_score', sa.Float, nullable=True),
        sa.Column('view_count', sa.BigInteger, default=0),
        sa.Column('embedding_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_segments_video_id', 'segments', ['video_id'])
    op.create_index('ix_segments_relevance_score', 'segments', ['relevance_score'])
    op.create_index('ix_segments_view_count', 'segments', ['view_count'])

    # Create segment_categories junction table
    op.create_table(
        'segment_categories',
        sa.Column('segment_id', sa.String(36), sa.ForeignKey('segments.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True),
    )

    # Create user_history table
    op.create_table(
        'user_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('segment_id', sa.String(36), sa.ForeignKey('segments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('watched_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('watch_duration', sa.Float, nullable=True),
        sa.Column('completed', sa.Boolean, default=False),
    )
    op.create_index('ix_user_history_user_id', 'user_history', ['user_id'])
    op.create_index('ix_user_history_watched_at', 'user_history', ['watched_at'])

    # Create saved_segments table
    op.create_table(
        'saved_segments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('segment_id', sa.String(36), sa.ForeignKey('segments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True),
        sa.UniqueConstraint('user_id', 'segment_id', name='uq_user_segment'),
    )
    op.create_index('ix_saved_segments_user_id', 'saved_segments', ['user_id'])


def downgrade() -> None:
    op.drop_table('saved_segments')
    op.drop_table('user_history')
    op.drop_table('segment_categories')
    op.drop_table('segments')
    op.drop_table('videos')
    op.drop_table('users')
    op.drop_table('categories')
    op.drop_table('channels')
