'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Segment } from '@/types';
import SegmentCard from '@/components/segments/SegmentCard';
import { Bookmark, Share2, Clock, User, ChevronDown, ChevronUp } from 'lucide-react';

declare global {
  interface Window {
    YT: {
      Player: new (elementId: string, options: YouTubePlayerOptions) => YouTubePlayer;
      PlayerState: {
        ENDED: number;
        PLAYING: number;
        PAUSED: number;
      };
    };
    onYouTubeIframeAPIReady: () => void;
  }
}

interface YouTubePlayerOptions {
  height: string;
  width: string;
  videoId: string;
  playerVars: {
    start?: number;
    end?: number;
    autoplay?: number;
    controls?: number;
    rel?: number;
    modestbranding?: number;
  };
  events: {
    onReady?: (event: { target: YouTubePlayer }) => void;
    onStateChange?: (event: { data: number }) => void;
  };
}

interface YouTubePlayer {
  destroy: () => void;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  playVideo: () => void;
  pauseVideo: () => void;
  getCurrentTime: () => number;
}

export default function WatchPage() {
  const params = useParams();
  const segmentId = params.id as string;
  
  const [segment, setSegment] = useState<Segment | null>(null);
  const [relatedSegments, setRelatedSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaved, setIsSaved] = useState(false);
  const [showFullTranscript, setShowFullTranscript] = useState(false);
  const playerRef = useRef<YouTubePlayer | null>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadSegment = async () => {
      setLoading(true);
      try {
        const [segmentData, related] = await Promise.all([
          api.getSegment(segmentId),
          api.getRelatedSegments(segmentId, 8),
        ]);
        setSegment(segmentData);
        setRelatedSegments(related);
        
        // Record view
        api.recordView(segmentId).catch(() => {});
      } catch (error) {
        console.error('Failed to load segment:', error);
      } finally {
        setLoading(false);
      }
    };

    if (segmentId) {
      loadSegment();
    }
  }, [segmentId]);

  useEffect(() => {
    if (!segment?.video?.youtube_id) return;

    // Load YouTube IFrame API
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = () => {
      if (playerContainerRef.current) {
        playerRef.current = new window.YT.Player('youtube-player', {
          height: '100%',
          width: '100%',
          videoId: segment.video!.youtube_id,
          playerVars: {
            start: Math.floor(segment.start_time),
            end: Math.ceil(segment.end_time),
            autoplay: 1,
            controls: 1,
            rel: 0,
            modestbranding: 1,
          },
          events: {
            onReady: (event) => {
              event.target.playVideo();
            },
            onStateChange: (event) => {
              // Loop the segment
              if (event.data === window.YT.PlayerState.ENDED) {
                playerRef.current?.seekTo(segment.start_time, true);
                playerRef.current?.playVideo();
              }
            },
          },
        });
      }
    };

    // If API is already loaded
    if (window.YT && window.YT.Player) {
      window.onYouTubeIframeAPIReady();
    }

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
      }
    };
  }, [segment]);

  const handleSave = async () => {
    try {
      if (isSaved) {
        await api.unsaveSegment(segmentId);
      } else {
        await api.saveSegment(segmentId);
      }
      setIsSaved(!isSaved);
    } catch (error) {
      console.error('Failed to save segment:', error);
    }
  };

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({
          title: segment?.generated_title || segment?.title,
          url,
        });
      } catch (error) {
        console.log('Share cancelled');
      }
    } else {
      navigator.clipboard.writeText(url);
      alert('Link copied to clipboard!');
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="animate-pulse bg-gray-800 aspect-video rounded-lg" />
              <div className="mt-4 space-y-3">
                <div className="h-6 bg-gray-800 rounded w-3/4" />
                <div className="h-4 bg-gray-700 rounded w-1/2" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!segment) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-2">Segment not found</h1>
          <p className="text-gray-400">This clip may have been removed or is unavailable.</p>
        </div>
      </div>
    );
  }

  const duration = segment.duration || (segment.end_time - segment.start_time);

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {/* Video Player */}
            <div ref={playerContainerRef} className="aspect-video bg-black rounded-lg overflow-hidden">
              <div id="youtube-player" />
            </div>

            {/* Video Info */}
            <div className="mt-4">
              <h1 className="text-xl sm:text-2xl font-bold text-white">
                {segment.generated_title || segment.title}
              </h1>

              <div className="flex flex-wrap items-center gap-4 mt-3 text-gray-400 text-sm">
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {formatDuration(duration)}
                </span>
                {segment.channel && (
                  <Link 
                    href={`/channel/${segment.channel.id}`}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 
                             rounded-full transition-colors group"
                  >
                    {segment.channel.thumbnail_url ? (
                      <img
                        src={segment.channel.thumbnail_url}
                        alt={segment.channel.name}
                        className="w-6 h-6 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 
                                    flex items-center justify-center">
                        <span className="text-xs font-bold text-white">
                          {segment.channel.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    )}
                    <span className="group-hover:text-white transition-colors">
                      {segment.channel.name}
                    </span>
                  </Link>
                )}
                {segment.view_count !== undefined && (
                  <span>{segment.view_count.toLocaleString()} views</span>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleSave}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 
                           rounded-lg text-white transition-colors"
                >
                  {isSaved ? (
                    <Bookmark className="h-5 w-5 text-primary-500 fill-current" />
                  ) : (
                    <Bookmark className="h-5 w-5" />
                  )}
                  {isSaved ? 'Saved' : 'Save'}
                </button>
                <button
                  onClick={handleShare}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 
                           rounded-lg text-white transition-colors"
                >
                  <Share2 className="h-5 w-5" />
                  Share
                </button>
              </div>

              {/* Summary & Key Takeaways */}
              <div className="mt-6 p-4 bg-gray-800 rounded-lg">
                <h2 className="font-semibold text-white mb-2">Summary</h2>
                <p className="text-gray-300 text-sm leading-relaxed">
                  {segment.summary_text || segment.summary || 'No summary available.'}
                </p>

                {segment.key_takeaways && segment.key_takeaways.length > 0 && (
                  <div className="mt-4">
                    <h3 className="font-semibold text-white mb-2">Key Takeaways</h3>
                    <ul className="space-y-2">
                      {segment.key_takeaways.map((takeaway, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm text-gray-300">
                          <span className="flex-shrink-0 w-5 h-5 bg-primary-600 text-white 
                                         rounded-full flex items-center justify-center text-xs">
                            {index + 1}
                          </span>
                          {takeaway}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Transcript */}
              {segment.transcript_chunk && (
                <div className="mt-4 p-4 bg-gray-800 rounded-lg">
                  <button
                    onClick={() => setShowFullTranscript(!showFullTranscript)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <h2 className="font-semibold text-white">Transcript</h2>
                    {showFullTranscript ? (
                      <ChevronUp className="h-5 w-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                  {showFullTranscript && (
                    <p className="mt-3 text-gray-300 text-sm leading-relaxed whitespace-pre-line">
                      {segment.transcript_chunk}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Related Segments Sidebar */}
          <div className="lg:col-span-1">
            <h2 className="text-lg font-semibold text-white mb-4">Related Clips</h2>
            <div className="space-y-4">
              {relatedSegments.map((related) => (
                <SegmentCard key={related.id} segment={related} compact />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
