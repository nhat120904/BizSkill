'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Segment } from '@/types';
import SegmentCard from '@/components/segments/SegmentCard';
import { Sparkles, Flame, Clock } from 'lucide-react';

type FeedType = 'trending' | 'latest' | 'recommended';

export default function FeedPage() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedType, setFeedType] = useState<FeedType>('trending');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    loadFeed(true);
  }, [feedType]);

  const loadFeed = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    setLoading(true);

    try {
      const result = await api.getFeed(feedType, currentPage, 20);
      if (reset) {
        setSegments(result.results);
        setPage(2);
      } else {
        setSegments((prev) => [...prev, ...result.results]);
        setPage((p) => p + 1);
      }
      setHasMore(result.results.length === 20);
    } catch (error) {
      console.error('Failed to load feed:', error);
    } finally {
      setLoading(false);
    }
  };

  const feedTabs = [
    { type: 'trending' as FeedType, label: 'Trending', icon: Flame },
    { type: 'latest' as FeedType, label: 'Latest', icon: Clock },
    { type: 'recommended' as FeedType, label: 'For You', icon: Sparkles },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-6 py-4">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Feed</h1>
            <div className="flex gap-2">
              {feedTabs.map(({ type, label, icon: Icon }) => (
                <button
                  key={type}
                  onClick={() => setFeedType(type)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium
                            transition-colors ${
                              feedType === type
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                            }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && segments.length === 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="bg-gray-300 dark:bg-gray-700 rounded-lg aspect-video mb-3" />
                <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded mb-2" />
                <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {segments.map((segment) => (
                <SegmentCard key={segment.id} segment={segment} />
              ))}
            </div>

            {/* Load More */}
            {hasMore && (
              <div className="flex justify-center mt-8">
                <button
                  onClick={() => loadFeed(false)}
                  disabled={loading}
                  className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium
                           hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors"
                >
                  {loading ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
