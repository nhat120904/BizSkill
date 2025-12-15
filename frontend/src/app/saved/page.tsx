'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Segment } from '@/types';
import SegmentCard from '@/components/segments/SegmentCard';
import { Bookmark } from 'lucide-react';
import Link from 'next/link';

export default function SavedPage() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    loadSaved();
  }, []);

  const loadSaved = async () => {
    setLoading(true);
    try {
      const saved = await api.getSavedSegments(1, 20);
      setSegments(saved);
      setPage(2);
      setHasMore(saved.length === 20);
    } catch (error) {
      console.error('Failed to load saved segments:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    try {
      const saved = await api.getSavedSegments(page, 20);
      setSegments((prev) => [...prev, ...saved]);
      setPage((p) => p + 1);
      setHasMore(saved.length === 20);
    } catch (error) {
      console.error('Failed to load more:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-1/4 mb-8" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i}>
                  <div className="bg-gray-300 dark:bg-gray-700 rounded-lg aspect-video mb-3" />
                  <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded mb-2" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-2/3" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Bookmark className="h-8 w-8 text-primary-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Saved Clips
          </h1>
        </div>

        {segments.length > 0 ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {segments.map((segment) => (
                <SegmentCard key={segment.id} segment={segment} />
              ))}
            </div>

            {hasMore && (
              <div className="flex justify-center mt-8">
                <button
                  onClick={loadMore}
                  className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium
                           hover:bg-primary-700 transition-colors"
                >
                  Load More
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-16">
            <Bookmark className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              No saved clips yet
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              Save clips to watch later by clicking the bookmark icon
            </p>
            <Link
              href="/feed"
              className="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg 
                       font-medium hover:bg-primary-700 transition-colors"
            >
              Explore Clips
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
