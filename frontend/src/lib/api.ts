import axios, { AxiosInstance, AxiosError } from 'axios';
import { Segment, Category, SearchResult, FeedResult, Channel, User, AuthResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.token = null;
          if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
          }
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('token', token);
      } else {
        localStorage.removeItem('token');
      }
    }
  }

  // ============ Feed & Discovery ============

  async getFeed(type: string = 'trending', page: number = 1, limit: number = 20): Promise<FeedResult> {
    const response = await this.client.get<FeedResult>('/segments/feed', {
      params: { type, page, limit },
    });
    return response.data;
  }

  async getTrending(page: number = 1, limit: number = 20): Promise<Segment[]> {
    const response = await this.client.get<{ segments: Segment[] }>('/segments', {
      params: { skip: (page - 1) * limit, limit, sort_by: 'view_count' },
    });
    return response.data.segments || [];
  }

  // ============ Search ============

  async search(
    query: string,
    options: {
      page?: number;
      limit?: number;
      category?: string;
      channel?: string;
      min_duration?: number;
      max_duration?: number;
    } = {}
  ): Promise<SearchResult> {
    const { page = 1, limit = 20, ...filters } = options;
    const response = await this.client.get<SearchResult>('/search', {
      params: {
        q: query,
        page,
        limit,
        ...filters,
      },
    });
    return response.data;
  }

  async getSearchSuggestions(query: string): Promise<string[]> {
    const response = await this.client.get<{ suggestions: string[] }>('/search/suggestions', {
      params: { q: query },
    });
    return response.data.suggestions || [];
  }

  // ============ Segments ============

  async getSegment(id: string): Promise<Segment> {
    const response = await this.client.get<Segment>(`/segments/${id}`);
    return response.data;
  }

  async getRelatedSegments(id: string, limit: number = 10): Promise<Segment[]> {
    const response = await this.client.get<{ segments: Segment[] }>(`/segments/${id}/related`, {
      params: { limit },
    });
    return response.data.segments || [];
  }

  async recordView(segmentId: string): Promise<void> {
    await this.client.post(`/segments/${segmentId}/view`);
  }

  // ============ Categories ============

  async getCategories(): Promise<Category[]> {
    const response = await this.client.get<Category[]>('/categories');
    return response.data || [];
  }

  async getCategoryBySlug(slug: string): Promise<Category> {
    const response = await this.client.get<Category>(`/categories/${slug}`);
    return response.data;
  }

  async getCategorySegments(
    slug: string,
    page: number = 1,
    limit: number = 20
  ): Promise<{ category: Category; segments: Segment[] }> {
    const response = await this.client.get<{ category: Category; segments: Segment[] }>(
      `/categories/${slug}/segments`,
      { params: { page, limit } }
    );
    return response.data;
  }

  // ============ Channels ============

  async getChannels(): Promise<Channel[]> {
    const response = await this.client.get<{ channels: Channel[] }>('/channels');
    return response.data.channels || [];
  }

  async getChannel(id: string): Promise<Channel> {
    const response = await this.client.get<Channel>(`/channels/${id}`);
    return response.data;
  }

  async getChannelSegments(channelId: string, page: number = 1, limit: number = 20): Promise<Segment[]> {
    const response = await this.client.get<{ segments: Segment[] }>(`/channels/${channelId}/segments`, {
      params: { page, limit },
    });
    return response.data.segments || [];
  }

  async getChannelWithSegments(channelId: string, page: number = 1, limit: number = 20): Promise<{
    channel: Channel & { segment_count?: number };
    segments: Segment[];
    total: number;
    page: number;
    pages: number;
  }> {
    const response = await this.client.get(`/channels/${channelId}/segments`, {
      params: { page, limit },
    });
    return response.data;
  }

  // ============ Auth ============

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login', {
      email,
      password,
    });
    
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(email: string, password: string, fullName?: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    
    this.setToken(response.data.access_token);
    return response.data;
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  // ============ User Actions ============

  async saveSegment(segmentId: string): Promise<void> {
    await this.client.post(`/users/me/saved/${segmentId}`);
  }

  async unsaveSegment(segmentId: string): Promise<void> {
    await this.client.delete(`/users/me/saved/${segmentId}`);
  }

  async getSavedSegments(page: number = 1, limit: number = 20): Promise<Segment[]> {
    const response = await this.client.get<{ segments: Segment[] }>('/users/me/saved', {
      params: { page, limit },
    });
    return response.data.segments || [];
  }

  async getWatchHistory(page: number = 1, limit: number = 20): Promise<Segment[]> {
    const response = await this.client.get<{ segments: Segment[] }>('/users/me/history', {
      params: { page, limit },
    });
    return response.data.segments || [];
  }
}

// Export singleton instance
export const api = new ApiClient();
export default api;
