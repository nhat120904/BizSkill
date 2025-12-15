"use client";

import Link from "next/link";
import Image from "next/image";
import { Play, Clock, Star } from "lucide-react";
import type { Segment } from "@/types";

interface SegmentCardProps {
  segment: Segment;
  compact?: boolean;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function SegmentCard({ segment, compact = false }: SegmentCardProps) {
  const thumbnailUrl =
    segment.video?.thumbnail_url ||
    `https://i.ytimg.com/vi/${segment.video?.youtube_id}/hqdefault.jpg`;

  if (compact) {
    return (
      <Link
        href={`/watch/${segment.id}`}
        className="group flex gap-3 p-2 rounded-lg hover:bg-gray-800 transition-colors"
      >
        <div className="relative w-40 flex-shrink-0 aspect-video bg-gray-700 rounded overflow-hidden">
          <Image
            src={thumbnailUrl}
            alt={segment.generated_title || segment.title || ''}
            fill
            className="object-cover"
            sizes="160px"
          />
          <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/80 text-white text-xs rounded">
            {formatDuration(segment.duration || segment.end_time - segment.start_time)}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-white line-clamp-2 group-hover:text-primary-400">
            {segment.generated_title || segment.title}
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            {segment.channel?.name}
          </p>
          {segment.view_count !== undefined && (
            <p className="text-xs text-gray-500 mt-1">
              {segment.view_count.toLocaleString()} views
            </p>
          )}
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/watch/${segment.id}`}
      className="group block bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 hover:shadow-xl transition-all duration-300"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-100">
        <Image
          src={thumbnailUrl}
          alt={segment.title || segment.generated_title}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
        />
        
        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
          <div className="w-12 h-12 bg-white/90 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity transform scale-90 group-hover:scale-100">
            <Play className="w-5 h-5 text-gray-900 ml-0.5" fill="currentColor" />
          </div>
        </div>
        
        {/* Duration badge */}
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/80 text-white text-xs font-medium rounded">
          {formatDuration(segment.duration || segment.end_time - segment.start_time)}
        </div>
        
        {/* Relevance score */}
        {segment.relevance_score && segment.relevance_score >= 8 && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-yellow-500 text-white text-xs font-medium rounded flex items-center gap-1">
            <Star className="w-3 h-3" fill="currentColor" />
            Top Pick
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-2 group-hover:text-primary-600 transition-colors">
          {segment.generated_title || segment.title}
        </h3>
        
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
          {segment.summary_text || segment.summary}
        </p>

        {/* Meta */}
        <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
          <span className="font-medium text-gray-600 dark:text-gray-300">
            {segment.channel?.name}
          </span>
          {segment.categories && segment.categories.length > 0 && (
            <>
              <span>•</span>
              <span>{segment.categories[0]}</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}

export default SegmentCard;
