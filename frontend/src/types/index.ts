export interface Channel {
  id: string;
  youtube_channel_id: string;
  name: string;
  description?: string;
  thumbnail_url?: string;
  custom_url?: string;
  subscriber_count?: string;
}

export interface Video {
  id?: string;
  youtube_id: string;
  original_title?: string;
  title?: string;
  description?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  duration?: number;
}

export interface Segment {
  id: string;
  generated_title?: string;
  title?: string;
  summary_text?: string;
  summary?: string;
  key_takeaways?: string[];
  relevance_score?: number;
  start_time: number;
  end_time: number;
  duration?: number;
  view_count?: number;
  transcript_chunk?: string;
  video?: Video;
  channel?: Channel;
  categories?: string[];
  search_score?: number;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  segment_count?: number;
}

export interface SearchResult {
  query: string;
  total: number;
  page: number;
  limit: number;
  results: Segment[];
}

export interface FeedResult {
  type: string;
  category?: string;
  page: number;
  limit: number;
  results: Segment[];
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ============ Learning Path Types ============

export interface LearningPathLesson {
  id: string;
  order: number;
  title?: string;
  description?: string;
  learning_objective?: string;
  context_notes?: string;
  key_concepts?: string[];
  is_completed: boolean;
  is_locked: boolean;
  completed_at?: string;
  segment?: Segment;
}

export interface LearningPath {
  id: string;
  title: string;
  description?: string;
  target_skill: string;
  current_level?: string;
  target_level?: string;
  skill_gap_analysis?: string;
  learning_objectives?: string[];
  estimated_hours?: number;
  status: 'draft' | 'active' | 'completed' | 'paused';
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  started_at?: string;
  completed_at?: string;
  last_activity_at?: string;
  created_at: string;
  lessons?: LearningPathLesson[];
}

export interface LearningPathCreateRequest {
  target_skill: string;
  current_level: number;
  target_level: number;
  goals?: string;
  time_commitment_hours?: number;
}

export interface SkillGapAnalysis {
  current_level: string;
  target_level: string;
  gap_description: string;
  key_areas_to_improve: string[];
  estimated_learning_hours: number;
  recommended_approach: string;
}

export interface NextLessonSuggestion {
  segment_id: string;
  reason: string;
  relevance_score: number;
  connects_to_previous: string;
}

export interface LessonCompleteResponse {
  lesson: LearningPathLesson;
  next_suggestion?: NextLessonSuggestion;
  path_completed: boolean;
}

export interface SuggestedSkill {
  skill: string;
  category_id: string;
  description?: string;
  icon?: string;
  color?: string;
  available_lessons: number;
  is_interest: boolean;
}
