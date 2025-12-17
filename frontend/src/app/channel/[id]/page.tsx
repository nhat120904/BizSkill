'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Segment, Channel } from '@/types';
import SegmentCard from '@/components/segments/SegmentCard';
import { Users, Video, ArrowLeft } from 'lucide-react';

interface ChannelPageData {
  channel: Channel & { segment_count?: number };
  segments: Segment[];
  total: number;
  page: number;
  pages: number;
}

export default function ChannelPage() {
  const params = useParams();
  const channelId = params.id as string;
  
  const [data, setData] = useState<ChannelPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    const loadChannel = async () => {
      setLoading(true);
      try {
        const result = await api.getChannelWithSegments(channelId, currentPage, 20);
        setData(result);
      } catch (error) {
        console.error('Failed to load channel:', error);
      } finally {
        setLoading(false);
      }
    };

    if (channelId) {
      loadChannel();
    }
  }, [channelId, currentPage]);

  const formatSubscribers = (count: string | undefined) => {
    if (!count) return 'N/A';
    const num = parseInt(count);
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return count;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Loading skeleton */}
          <div className="animate-pulse">
            <div className="flex items-center gap-6 mb-8">
              <div className="w-24 h-24 bg-gray-800 rounded-full" />
              <div className="flex-1">
                <div className="h-8 bg-gray-800 rounded w-64 mb-2" />
                <div className="h-4 bg-gray-700 rounded w-32" />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="bg-gray-800 rounded-lg aspect-video" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data || !data.channel) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-2">Channel not found</h1>
          <p className="text-gray-400 mb-4">This channel may have been removed or is unavailable.</p>
          <Link href="/" className="text-primary-500 hover:text-primary-400">
            Go back home
          </Link>
        </div>
      </div>
    );
  }

  const { channel, segments, total, pages } = data;

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Back button */}
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>

        {/* Channel Header */}
        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
            {/* Channel Avatar */}
            {channel.thumbnail_url ? (
              <img
                src={channel.thumbnail_url}
                alt={channel.name}
                className="w-24 h-24 sm:w-32 sm:h-32 rounded-full object-cover border-4 border-gray-700"
              />
            ) : (
              <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center">
                <span className="text-3xl sm:text-4xl font-bold text-white">
                  {channel.name.charAt(0).toUpperCase()}
                </span>
              </div>
            )}

            {/* Channel Info */}
            <div className="flex-1 text-center sm:text-left">
              <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
                {channel.name}
              </h1>
              
              {channel.custom_url && (
                <p className="text-gray-400 mb-3">{channel.custom_url}</p>
              )}

              <div className="flex flex-wrap justify-center sm:justify-start gap-4 text-sm text-gray-400">
                {channel.subscriber_count && (
                  <span className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {formatSubscribers(channel.subscriber_count)} subscribers
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Video className="h-4 w-4" />
                  {channel.segment_count || total} shorts
                </span>
              </div>

              {channel.description && (
                <p className="mt-4 text-gray-300 text-sm line-clamp-3">
                  {channel.description}
                </p>
              )}
            </div>

            {/* YouTube Link */}
            <a
              href={`https://www.youtube.com/channel/${channel.youtube_channel_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg 
                       transition-colors flex items-center gap-2"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              YouTube
            </a>
          </div>
        </div>

        {/* Segments Grid */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">
            All Shorts ({total})
          </h2>
        </div>

        {segments.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400">No shorts available from this channel yet.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {segments.map((segment) => (
                <SegmentCard key={segment.id} segment={segment} />
              ))}
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex justify-center gap-2 mt-8">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 
                           disabled:cursor-not-allowed rounded-lg text-white transition-colors"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-gray-400">
                  Page {currentPage} of {pages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(pages, p + 1))}
                  disabled={currentPage === pages}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 
                           disabled:cursor-not-allowed rounded-lg text-white transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
