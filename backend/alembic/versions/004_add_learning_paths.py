"""add learning path tables

Revision ID: 004
Revises: 003_add_cloudinary_fields
Create Date: 2024-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '004_add_learning_paths'
down_revision = '003_add_cloudinary_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create learning_paths table
    op.create_table(
        'learning_paths',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Path metadata
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('target_skill', sa.String(200), nullable=False),
        sa.Column('current_level', sa.String(50)),
        sa.Column('target_level', sa.String(50)),
        
        # AI-generated content
        sa.Column('skill_gap_analysis', sa.Text()),
        sa.Column('learning_objectives', JSONB()),
        sa.Column('estimated_hours', sa.Float()),
        
        # Progress tracking
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('progress_percentage', sa.Float(), default=0.0),
        sa.Column('completed_lessons', sa.Integer(), default=0),
        sa.Column('total_lessons', sa.Integer(), default=0),
        
        # Timestamps
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('last_activity_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on status for filtering
    op.create_index('ix_learning_paths_status', 'learning_paths', ['status'])
    op.create_index('ix_learning_paths_target_skill', 'learning_paths', ['target_skill'])
    
    # Create learning_path_lessons table
    op.create_table(
        'learning_path_lessons',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('learning_path_id', sa.String(36), sa.ForeignKey('learning_paths.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('segment_id', sa.String(36), sa.ForeignKey('segments.id', ondelete='SET NULL'), nullable=True),
        
        # Lesson details
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(300)),
        sa.Column('description', sa.Text()),
        sa.Column('learning_objective', sa.Text()),
        
        # AI-generated context
        sa.Column('context_notes', sa.Text()),
        sa.Column('prerequisites', JSONB()),
        sa.Column('key_concepts', JSONB()),
        
        # Progress
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('is_locked', sa.Boolean(), default=False),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('watch_progress_seconds', sa.Integer(), default=0),
        
        # Assessment
        sa.Column('quiz_questions', JSONB()),
        sa.Column('quiz_score', sa.Float()),
        
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for lessons
    op.create_index('ix_learning_path_lessons_order', 'learning_path_lessons', ['learning_path_id', 'order'])
    op.create_index('ix_learning_path_lessons_completed', 'learning_path_lessons', ['is_completed'])
    
    # Create skill_assessments table
    op.create_table(
        'skill_assessments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Assessment details
        sa.Column('skill_name', sa.String(200), nullable=False),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id', ondelete='SET NULL')),
        
        # Self-assessment
        sa.Column('current_level', sa.Integer()),
        sa.Column('target_level', sa.Integer()),
        sa.Column('confidence', sa.Integer()),
        
        # Additional context
        sa.Column('experience_description', sa.Text()),
        sa.Column('goals', sa.Text()),
        sa.Column('time_commitment_hours', sa.Float()),
        
        # AI analysis
        sa.Column('ai_assessed_level', sa.Integer()),
        sa.Column('ai_recommendations', JSONB()),
        
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index for skill assessments
    op.create_index('ix_skill_assessments_skill', 'skill_assessments', ['skill_name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_skill_assessments_skill', table_name='skill_assessments')
    op.drop_index('ix_learning_path_lessons_completed', table_name='learning_path_lessons')
    op.drop_index('ix_learning_path_lessons_order', table_name='learning_path_lessons')
    op.drop_index('ix_learning_paths_target_skill', table_name='learning_paths')
    op.drop_index('ix_learning_paths_status', table_name='learning_paths')
    
    # Drop tables
    op.drop_table('skill_assessments')
    op.drop_table('learning_path_lessons')
    op.drop_table('learning_paths')
