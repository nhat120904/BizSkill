'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { Segment, Category } from '@/types';
import SegmentCard from '@/components/segments/SegmentCard';

export default function CategoryPage() {
  const params = useParams();
  const slug = params.slug as string;
  
  const [category, setCategory] = useState<Category | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    loadCategory();
  }, [slug]);

  const loadCategory = async () => {
    setLoading(true);
    try {
      const result = await api.getCategorySegments(slug, 1, 20);
      setCategory(result.category);
      setSegments(result.segments);
      setPage(2);
      setHasMore(result.segments.length === 20);
    } catch (error) {
      console.error('Failed to load category:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    try {
      const result = await api.getCategorySegments(slug, page, 20);
      setSegments((prev) => [...prev, ...result.segments]);
      setPage((p) => p + 1);
      setHasMore(result.segments.length === 20);
    } catch (error) {
      console.error('Failed to load more segments:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-1/4 mb-4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-1/2 mb-8" />
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

  if (!category) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Category not found
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            This category doesn&apos;t exist or has been removed.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-4">
            {category.icon && (
              <span className="text-4xl">{category.icon}</span>
            )}
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
                {category.name}
              </h1>
              {category.description && (
                <p className="mt-1 text-gray-500 dark:text-gray-400">
                  {category.description}
                </p>
              )}
              {category.segment_count !== undefined && (
                <p className="mt-2 text-sm text-gray-400">
                  {category.segment_count.toLocaleString()} clips
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Segments */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
            <p className="text-gray-500 dark:text-gray-400">
              No clips in this category yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
