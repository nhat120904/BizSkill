"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { 
  ArrowLeft, ArrowRight, CheckCircle2, PlayCircle, 
  Loader2, AlertCircle, BookOpen, Target, Sparkles,
  Clock, ChevronRight
} from "lucide-react";
import { api } from "@/lib/api";
import type { LearningPath, LearningPathLesson, NextLessonSuggestion } from "@/types";

export default function LessonPage() {
  const router = useRouter();
  const params = useParams();
  const pathId = params.id as string;
  const lessonId = params.lessonId as string;

  const [path, setPath] = useState<LearningPath | null>(null);
  const [lesson, setLesson] = useState<LearningPathLesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextSuggestion, setNextSuggestion] = useState<NextLessonSuggestion | null>(null);
  const [showComplete, setShowComplete] = useState(false);

  useEffect(() => {
    if (pathId && lessonId) {
      loadData();
    }
  }, [pathId, lessonId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pathData, lessonData] = await Promise.all([
        api.getLearningPath(pathId),
        api.getLesson(pathId, lessonId),
      ]);
      setPath(pathData);
      setLesson(lessonData);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push(`/login?redirect=/learn/${pathId}/lesson/${lessonId}`);
        return;
      }
      setError(err.response?.data?.detail || "Failed to load lesson");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!lesson || lesson.is_completed) return;
    
    setCompleting(true);
    try {
      const result = await api.completeLesson(pathId, lessonId);
      setLesson(result.lesson);
      setNextSuggestion(result.next_suggestion || null);
      setShowComplete(true);
      
      // Update path progress locally
      if (path) {
        setPath({
          ...path,
          completed_lessons: path.completed_lessons + 1,
          progress_percentage: ((path.completed_lessons + 1) / path.total_lessons) * 100,
          status: result.path_completed ? "completed" : path.status,
        });
      }
    } catch (err: any) {
      console.error("Failed to complete lesson:", err);
    } finally {
      setCompleting(false);
    }
  };

  const segment = lesson?.segment;
  const youtubeUrl = segment?.video?.youtube_id 
    ? `https://www.youtube.com/embed/${segment.video.youtube_id}?start=${Math.floor(segment.start_time)}&end=${Math.floor(segment.end_time)}&autoplay=1`
    : null;

  // Find previous and next lessons
  const currentIndex = path?.lessons?.findIndex((l) => l.id === lessonId) ?? -1;
  const prevLesson = currentIndex > 0 ? path?.lessons?.[currentIndex - 1] : null;
  const nextLesson = currentIndex >= 0 && currentIndex < (path?.lessons?.length || 0) - 1 
    ? path?.lessons?.[currentIndex + 1] 
    : null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (error || !lesson || !path) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {error || "Lesson not found"}
        </h1>
        <Link
          href={`/learn/${pathId}`}
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          Back to Learning Path
        </Link>
      </div>
    );
  }

  // Completion celebration screen
  if (showComplete) {
    const isPathComplete = path.status === "completed";
    
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-purple-50">
        <div className="max-w-lg mx-auto text-center p-8">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10 text-green-600" />
          </div>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {isPathComplete ? "🎉 Congratulations!" : "Lesson Complete!"}
          </h1>
          
          <p className="text-gray-600 mb-8">
            {isPathComplete 
              ? `You've completed the entire "${path.title}" learning path!`
              : `Great job! You've completed "${lesson.title}"`
            }
          </p>

          {/* Progress update */}
          <div className="bg-white rounded-xl p-4 mb-6 border border-gray-200">
            <div className="text-sm text-gray-500 mb-2">Path Progress</div>
            <div className="flex items-center gap-4">
              <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary-600 rounded-full transition-all duration-1000"
                  style={{ width: `${path.progress_percentage}%` }}
                />
              </div>
              <span className="font-bold text-primary-600">
                {Math.round(path.progress_percentage)}%
              </span>
            </div>
            <div className="text-sm text-gray-600 mt-2">
              {path.completed_lessons} of {path.total_lessons} lessons completed
            </div>
          </div>

          {/* AI Suggestion for next lesson */}
          {nextSuggestion && !isPathComplete && (
            <div className="bg-purple-50 rounded-xl p-4 mb-6 text-left border border-purple-200">
              <div className="flex items-center gap-2 text-purple-700 font-medium mb-2">
                <Sparkles className="w-4 h-4" />
                AI Recommendation
              </div>
              <p className="text-sm text-purple-800 mb-3">
                {nextSuggestion.reason}
              </p>
              <div className="text-xs text-purple-600">
                {nextSuggestion.connects_to_previous}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href={`/learn/${pathId}`}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg 
                       hover:bg-gray-50 transition-colors font-medium"
            >
              View Path
            </Link>
            
            {nextLesson && !nextLesson.is_locked && !isPathComplete && (
              <Link
                href={`/learn/${pathId}/lesson/${nextLesson.id}`}
                onClick={() => setShowComplete(false)}
                className="flex-1 px-4 py-3 bg-primary-600 text-white rounded-lg 
                         hover:bg-primary-700 transition-colors font-medium flex items-center 
                         justify-center gap-2"
              >
                Next Lesson
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
            
            {isPathComplete && (
              <Link
                href="/learn"
                className="flex-1 px-4 py-3 bg-primary-600 text-white rounded-lg 
                         hover:bg-primary-700 transition-colors font-medium"
              >
                Explore More Paths
              </Link>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link
              href={`/learn/${pathId}`}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">{path.title}</span>
            </Link>
            
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Target className="w-4 h-4" />
              <span>Lesson {lesson.order} of {path.total_lessons}</span>
            </div>

            <div className="flex items-center gap-2">
              {prevLesson && (
                <Link
                  href={`/learn/${pathId}/lesson/${prevLesson.id}`}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
                  title="Previous lesson"
                >
                  <ArrowLeft className="w-5 h-5" />
                </Link>
              )}
              {nextLesson && !nextLesson.is_locked && (
                <Link
                  href={`/learn/${pathId}/lesson/${nextLesson.id}`}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
                  title="Next lesson"
                >
                  <ArrowRight className="w-5 h-5" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content - Video */}
          <div className="lg:col-span-2">
            {/* Video Player */}
            {youtubeUrl ? (
              <div className="aspect-video bg-black rounded-xl overflow-hidden mb-6">
                <iframe
                  src={youtubeUrl}
                  title={lesson.title || "Lesson video"}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="w-full h-full"
                />
              </div>
            ) : (
              <div className="aspect-video bg-gray-200 rounded-xl flex items-center justify-center mb-6">
                <div className="text-center text-gray-500">
                  <PlayCircle className="w-16 h-16 mx-auto mb-2" />
                  <p>Video not available</p>
                </div>
              </div>
            )}

            {/* Lesson Title & Info */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    {lesson.title || segment?.generated_title}
                  </h1>
                  {segment?.channel?.name && (
                    <p className="text-gray-600">
                      From: <span className="font-medium">{segment.channel.name}</span>
                    </p>
                  )}
                </div>
                
                {!lesson.is_completed && (
                  <button
                    onClick={handleComplete}
                    disabled={completing}
                    className="flex-shrink-0 px-4 py-2 bg-green-600 text-white rounded-lg 
                             hover:bg-green-700 transition-colors flex items-center gap-2
                             disabled:opacity-50"
                  >
                    {completing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Completing...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        Mark Complete
                      </>
                    )}
                  </button>
                )}
                
                {lesson.is_completed && (
                  <span className="flex items-center gap-1 px-3 py-1.5 bg-green-100 
                                 text-green-700 rounded-lg text-sm font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    Completed
                  </span>
                )}
              </div>

              {/* Meta info */}
              <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
                {segment && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {Math.round((segment.end_time - segment.start_time) / 60)} min
                  </span>
                )}
              </div>
            </div>

            {/* Learning Objective */}
            {lesson.learning_objective && (
              <div className="bg-primary-50 rounded-xl p-6 mb-6 border border-primary-100">
                <h3 className="font-semibold text-primary-900 mb-2 flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  What You&apos;ll Learn
                </h3>
                <p className="text-primary-800">{lesson.learning_objective}</p>
              </div>
            )}

            {/* Description */}
            {lesson.description && (
              <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">About This Lesson</h3>
                <p className="text-gray-700">{lesson.description}</p>
              </div>
            )}

            {/* Key Concepts */}
            {lesson.key_concepts && lesson.key_concepts.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">Key Concepts</h3>
                <div className="flex flex-wrap gap-2">
                  {lesson.key_concepts.map((concept, i) => (
                    <span
                      key={i}
                      className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm"
                    >
                      {concept}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Segment Details */}
            {segment?.summary_text && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-semibold text-gray-900 mb-3">Summary</h3>
                <p className="text-gray-700">{segment.summary_text}</p>
                
                {segment.key_takeaways && segment.key_takeaways.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <h4 className="font-medium text-gray-900 mb-2">Key Takeaways</h4>
                    <ul className="space-y-2">
                      {segment.key_takeaways.map((takeaway, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-1" />
                          <span className="text-gray-700">{takeaway}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar - Path Progress */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-6">
              {/* Progress Card */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Path Progress</h3>
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">
                      {path.completed_lessons} of {path.total_lessons} lessons
                    </span>
                    <span className="font-medium text-primary-600">
                      {Math.round(path.progress_percentage)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 rounded-full transition-all"
                      style={{ width: `${path.progress_percentage}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* AI Context */}
              {lesson.context_notes && (
                <div className="bg-purple-50 rounded-xl p-6 border border-purple-100">
                  <h3 className="font-semibold text-purple-900 mb-2 flex items-center gap-2">
                    <Sparkles className="w-5 h-5" />
                    Why This Lesson?
                  </h3>
                  <p className="text-purple-800 text-sm">{lesson.context_notes}</p>
                </div>
              )}

              {/* Up Next */}
              {nextLesson && !nextLesson.is_locked && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Up Next</h3>
                  <Link
                    href={`/learn/${pathId}/lesson/${nextLesson.id}`}
                    className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs text-gray-500 mb-1">
                          Lesson {nextLesson.order}
                        </div>
                        <div className="font-medium text-gray-900 line-clamp-2">
                          {nextLesson.title}
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </Link>
                </div>
              )}

              {/* View Full Path */}
              <Link
                href={`/learn/${pathId}`}
                className="flex items-center justify-center gap-2 w-full px-4 py-3 border 
                         border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 
                         transition-colors font-medium"
              >
                <BookOpen className="w-4 h-4" />
                View Full Path
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
