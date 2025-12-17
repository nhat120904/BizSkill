"use client";

import Link from "next/link";
import Image from "next/image";
import { 
  CheckCircle2, Lock, PlayCircle, Clock, 
  ChevronRight, Sparkles 
} from "lucide-react";
import type { LearningPathLesson } from "@/types";

interface LessonItemProps {
  lesson: LearningPathLesson;
  pathId: string;
  isActive?: boolean;
  onComplete?: () => void;
}

export function LessonItem({ lesson, pathId, isActive, onComplete }: LessonItemProps) {
  const segment = lesson.segment;
  const thumbnailUrl = segment?.video?.thumbnail_url || 
    (segment?.video?.youtube_id ? `https://i.ytimg.com/vi/${segment.video.youtube_id}/hqdefault.jpg` : null);

  const duration = segment ? Math.round((segment.end_time - segment.start_time) / 60) : 0;

  return (
    <div 
      className={`relative flex gap-4 p-4 rounded-xl transition-all ${
        lesson.is_locked 
          ? "bg-gray-50 opacity-60" 
          : isActive 
            ? "bg-primary-50 border-2 border-primary-500" 
            : lesson.is_completed 
              ? "bg-green-50 border border-green-200" 
              : "bg-white border border-gray-200 hover:border-gray-300"
      }`}
    >
      {/* Order Number */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
        lesson.is_completed 
          ? "bg-green-500 text-white" 
          : lesson.is_locked 
            ? "bg-gray-300 text-gray-500"
            : isActive
              ? "bg-primary-600 text-white"
              : "bg-gray-200 text-gray-700"
      }`}>
        {lesson.is_completed ? (
          <CheckCircle2 className="w-5 h-5" />
        ) : lesson.is_locked ? (
          <Lock className="w-4 h-4" />
        ) : (
          lesson.order
        )}
      </div>

      {/* Thumbnail */}
      {thumbnailUrl && !lesson.is_locked && (
        <div className="flex-shrink-0 relative w-32 aspect-video rounded-lg overflow-hidden bg-gray-200">
          <Image
            src={thumbnailUrl}
            alt={lesson.title || "Lesson thumbnail"}
            fill
            className="object-cover"
            sizes="128px"
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity">
            <PlayCircle className="w-10 h-10 text-white" />
          </div>
          {duration > 0 && (
            <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/80 text-white text-xs rounded">
              {duration}m
            </div>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h4 className={`font-medium line-clamp-1 ${
              lesson.is_locked ? "text-gray-500" : "text-gray-900"
            }`}>
              {lesson.title || segment?.generated_title || `Lesson ${lesson.order}`}
            </h4>
            {lesson.learning_objective && (
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {lesson.learning_objective}
              </p>
            )}
          </div>

          {!lesson.is_locked && !lesson.is_completed && (
            <Link
              href={`/learn/${pathId}/lesson/${lesson.id}`}
              className="flex-shrink-0 px-3 py-1.5 bg-primary-600 text-white text-sm 
                       rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-1"
            >
              {isActive ? "Continue" : "Start"}
              <ChevronRight className="w-4 h-4" />
            </Link>
          )}

          {lesson.is_completed && (
            <Link
              href={`/learn/${pathId}/lesson/${lesson.id}`}
              className="flex-shrink-0 px-3 py-1.5 border border-gray-300 text-gray-700 text-sm 
                       rounded-lg hover:bg-gray-50 transition-colors"
            >
              Review
            </Link>
          )}
        </div>

        {/* Key Concepts */}
        {lesson.key_concepts && lesson.key_concepts.length > 0 && !lesson.is_locked && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {lesson.key_concepts.slice(0, 3).map((concept, i) => (
              <span 
                key={i}
                className="inline-flex items-center px-2 py-0.5 bg-gray-100 text-gray-600 
                         text-xs rounded-full"
              >
                {concept}
              </span>
            ))}
          </div>
        )}

        {/* Context Notes */}
        {lesson.context_notes && !lesson.is_locked && (
          <div className="mt-2 flex items-start gap-1.5 text-xs text-primary-600">
            <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>{lesson.context_notes}</span>
          </div>
        )}

        {/* Meta */}
        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
          {duration > 0 && (
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {duration} min
            </span>
          )}
          {lesson.completed_at && (
            <span className="text-green-600">
              Completed {new Date(lesson.completed_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
