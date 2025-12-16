'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { Segment } from '@/types';
import { 
  Sparkles, Flame, Clock, Play, Pause, Volume2, VolumeX, 
  Bookmark, ChevronUp, ChevronDown, User, ExternalLink, Info
} from 'lucide-react';
import Link from 'next/link';

type FeedType = 'trending' | 'latest' | 'recommended';

interface ShortPlayerProps {
  segment: Segment;
  isActive: boolean;
  isMuted: boolean;
  onToggleMute: () => void;
}

function ShortPlayer({ segment, isActive, isMuted, onToggleMute }: ShortPlayerProps) {
  const playerRef = useRef<YT.Player | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [saved, setSaved] = useState(false);

  // Load YouTube IFrame API
  useEffect(() => {
    if (typeof window !== 'undefined' && !window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);
    }
  }, []);

  // Initialize player
  useEffect(() => {
    const initPlayer = () => {
      if (!containerRef.current || playerRef.current) return;
      
      const playerId = `player-${segment.id}`;
      const playerDiv = document.getElementById(playerId);
      if (!playerDiv) return;

      playerRef.current = new window.YT.Player(playerId, {
        videoId: segment.video?.youtube_id,
        playerVars: {
          autoplay: 0,
          controls: 0,
          modestbranding: 1,
          rel: 0,
          showinfo: 0,
          start: Math.floor(segment.start_time || 0),
          end: Math.ceil(segment.end_time || 0),
          playsinline: 1,
          loop: 1,
          mute: isMuted ? 1 : 0,
        },
        events: {
          onReady: () => setIsReady(true),
          onStateChange: (event: YT.OnStateChangeEvent) => {
            if (event.data === window.YT.PlayerState.ENDED) {
              // Loop back to start
              playerRef.current?.seekTo(segment.start_time || 0, true);
              playerRef.current?.playVideo();
            }
            setIsPlaying(event.data === window.YT.PlayerState.PLAYING);
          },
        },
      });
    };

    if (window.YT && window.YT.Player) {
      initPlayer();
    } else {
      window.onYouTubeIframeAPIReady = initPlayer;
    }

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [segment.id, segment.video?.youtube_id, segment.start_time, segment.end_time]);

  // Handle active state changes
  useEffect(() => {
    if (!isReady || !playerRef.current) return;

    if (isActive) {
      playerRef.current.seekTo(segment.start_time || 0, true);
      playerRef.current.playVideo();
    } else {
      playerRef.current.pauseVideo();
    }
  }, [isActive, isReady, segment.start_time]);

  // Handle mute changes
  useEffect(() => {
    if (!playerRef.current || !isReady) return;
    if (isMuted) {
      playerRef.current.mute();
    } else {
      playerRef.current.unMute();
    }
  }, [isMuted, isReady]);

  const togglePlay = () => {
    if (!playerRef.current) return;
    if (isPlaying) {
      playerRef.current.pauseVideo();
    } else {
      playerRef.current.playVideo();
    }
  };

  const handleSave = async () => {
    try {
      if (saved) {
        await api.unsaveSegment(segment.id);
      } else {
        await api.saveSegment(segment.id);
      }
      setSaved(!saved);
    } catch (error) {
      console.error('Failed to save segment:', error);
    }
  };

  const duration = (segment.end_time || 0) - (segment.start_time || 0);

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-full bg-black flex items-center justify-center"
    >
      {/* YouTube Player */}
      <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
        <div 
          id={`player-${segment.id}`}
          className="w-full h-full"
          style={{ 
            pointerEvents: 'none',
            minWidth: '177.78vh', // 16:9 aspect ratio to cover
            minHeight: '100vh',
          }}
        />
      </div>

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/80 pointer-events-none" />

      {/* Play/Pause Overlay */}
      <button 
        onClick={togglePlay}
        className="absolute inset-0 flex items-center justify-center z-10"
      >
        {!isPlaying && isReady && (
          <div className="w-20 h-20 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
            <Play className="w-10 h-10 text-white ml-1" fill="white" />
          </div>
        )}
      </button>

      {/* Right Side Actions */}
      <div className="absolute right-4 bottom-32 flex flex-col items-center gap-6 z-20">
        {/* Channel Avatar */}
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 rounded-full bg-primary-600 flex items-center justify-center border-2 border-white">
            {segment.channel?.thumbnail_url ? (
              <img src={segment.channel.thumbnail_url} alt="" className="w-full h-full rounded-full object-cover" />
            ) : (
              <User className="w-6 h-6 text-white" />
            )}
          </div>
          <div className="w-6 h-6 -mt-3 bg-primary-600 rounded-full flex items-center justify-center">
            <span className="text-white text-xs font-bold">+</span>
          </div>
        </div>

        {/* Detail/Watch Page */}
        <Link href={`/watch/${segment.id}`} className="flex flex-col items-center gap-1 group">
          <div className="w-12 h-12 bg-white/10 backdrop-blur-sm rounded-full flex items-center justify-center group-hover:bg-white/20 transition-colors">
            <Info className="w-6 h-6 text-white" />
          </div>
          <span className="text-white text-xs font-medium">Detail</span>
        </Link>

        {/* Save */}
        <button onClick={handleSave} className="flex flex-col items-center gap-1 group">
          <div className={`w-12 h-12 backdrop-blur-sm rounded-full flex items-center justify-center transition-colors
                          ${saved ? 'bg-primary-600' : 'bg-white/10 group-hover:bg-white/20'}`}>
            <Bookmark className={`w-6 h-6 ${saved ? 'text-white fill-white' : 'text-white'}`} />
          </div>
          <span className="text-white text-xs font-medium">Save</span>
        </button>

        {/* Mute/Unmute */}
        <button onClick={onToggleMute} className="flex flex-col items-center gap-1 group">
          <div className="w-12 h-12 bg-white/10 backdrop-blur-sm rounded-full flex items-center justify-center group-hover:bg-white/20 transition-colors">
            {isMuted ? (
              <VolumeX className="w-6 h-6 text-white" />
            ) : (
              <Volume2 className="w-6 h-6 text-white" />
            )}
          </div>
        </button>
      </div>

      {/* Bottom Info */}
      <div className="absolute bottom-6 left-4 right-20 z-20">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-white font-bold">@{segment.channel?.name || 'Unknown'}</span>
          <span className="text-white/60 text-sm">• {Math.round(duration)}s</span>
        </div>
        <h2 className="text-white font-semibold text-lg mb-2 line-clamp-2">
          {segment.title}
        </h2>
        <p className="text-white/80 text-sm line-clamp-2">
          {segment.summary}
        </p>
        
        {/* Key Takeaways */}
        {segment.key_takeaways && segment.key_takeaways.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {segment.key_takeaways.slice(0, 3).map((takeaway, i) => (
              <span key={i} className="px-2 py-1 bg-white/10 backdrop-blur-sm rounded-full text-white text-xs">
                💡 {takeaway.length > 30 ? takeaway.slice(0, 30) + '...' : takeaway}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Loading State */}
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black z-30">
          <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}

export default function FeedPage() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedType, setFeedType] = useState<FeedType>('trending');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

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
        setCurrentIndex(0);
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

  // Handle scroll/swipe
  const goToNext = useCallback(() => {
    if (currentIndex < segments.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      // Load more when near end
      if (currentIndex >= segments.length - 3 && hasMore && !loading) {
        loadFeed(false);
      }
    }
  }, [currentIndex, segments.length, hasMore, loading]);

  const goToPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  }, [currentIndex]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'j') {
        goToNext();
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        goToPrev();
      } else if (e.key === 'm') {
        setIsMuted((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToNext, goToPrev]);

  // Touch/Wheel scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let touchStartY = 0;
    let lastScrollTime = 0;
    const scrollCooldown = 500; // ms

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const now = Date.now();
      if (now - lastScrollTime < scrollCooldown) return;
      
      if (e.deltaY > 50) {
        goToNext();
        lastScrollTime = now;
      } else if (e.deltaY < -50) {
        goToPrev();
        lastScrollTime = now;
      }
    };

    const handleTouchStart = (e: TouchEvent) => {
      touchStartY = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndY = e.changedTouches[0].clientY;
      const diff = touchStartY - touchEndY;
      
      if (Math.abs(diff) > 50) {
        if (diff > 0) {
          goToNext();
        } else {
          goToPrev();
        }
      }
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('touchstart', handleTouchStart);
    container.addEventListener('touchend', handleTouchEnd);

    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [goToNext, goToPrev]);

  const feedTabs = [
    { type: 'trending' as FeedType, label: 'Trending', icon: Flame },
    { type: 'latest' as FeedType, label: 'Latest', icon: Clock },
    { type: 'recommended' as FeedType, label: 'For You', icon: Sparkles },
  ];

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 bg-black overflow-hidden"
      style={{ top: '64px', height: 'calc(100vh - 64px)' }}
    >
      {/* Feed Type Tabs - Floating */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-30 flex gap-2 bg-black/30 backdrop-blur-md rounded-full p-1">
        {feedTabs.map(({ type, label, icon: Icon }) => (
          <button
            key={type}
            onClick={() => setFeedType(type)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-colors
                      ${feedType === type
                        ? 'bg-white text-black'
                        : 'text-white/80 hover:text-white'
                      }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Navigation Arrows */}
      <div className="absolute right-4 top-1/2 transform -translate-y-1/2 z-30 flex flex-col gap-2">
        <button
          onClick={goToPrev}
          disabled={currentIndex === 0}
          className={`w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center
                     transition-opacity ${currentIndex === 0 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-white/20'}`}
        >
          <ChevronUp className="w-6 h-6 text-white" />
        </button>
        <button
          onClick={goToNext}
          disabled={currentIndex >= segments.length - 1}
          className={`w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center
                     transition-opacity ${currentIndex >= segments.length - 1 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-white/20'}`}
        >
          <ChevronDown className="w-6 h-6 text-white" />
        </button>
      </div>

      {/* Progress Indicator */}
      <div className="absolute left-4 top-1/2 transform -translate-y-1/2 z-30 flex flex-col gap-1">
        {segments.slice(Math.max(0, currentIndex - 3), currentIndex + 4).map((_, i) => {
          const actualIndex = Math.max(0, currentIndex - 3) + i;
          return (
            <div
              key={actualIndex}
              className={`w-1 rounded-full transition-all ${
                actualIndex === currentIndex 
                  ? 'h-6 bg-white' 
                  : 'h-2 bg-white/30'
              }`}
            />
          );
        })}
      </div>

      {/* Video Container */}
      {loading && segments.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-white/20 border-t-white rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white/60">Loading shorts...</p>
          </div>
        </div>
      ) : (
        <div 
          className="h-full transition-transform duration-300 ease-out"
          style={{ transform: `translateY(-${currentIndex * 100}%)` }}
        >
          {segments.map((segment, index) => (
            <div 
              key={segment.id} 
              className="h-full w-full"
              style={{ height: 'calc(100vh - 64px)' }}
            >
              <ShortPlayer
                segment={segment}
                isActive={index === currentIndex}
                isMuted={isMuted}
                onToggleMute={() => setIsMuted(!isMuted)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Keyboard Hints */}
      <div className="absolute bottom-4 left-4 z-30 text-white/40 text-xs hidden md:block">
        <span>↑↓ Navigate</span> • <span>M Mute</span>
      </div>
    </div>
  );
}
