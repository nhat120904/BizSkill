export interface Channel {
  id?: string;
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
