"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { 
  ArrowLeft, Target, Play, Pause, Trash2, 
  Loader2, AlertCircle, CheckCircle2, Share2
} from "lucide-react";
import { api } from "@/lib/api";
import { LessonItem, PathProgress } from "@/components/learning-paths";
import type { LearningPath } from "@/types";

export default function LearningPathDetailPage() {
  const router = useRouter();
  const params = useParams();
  const pathId = params.id as string;

  const [path, setPath] = useState<LearningPath | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (pathId) {
      loadPath();
    }
  }, [pathId]);

  const loadPath = async () => {
    try {
      setLoading(true);
      const data = await api.getLearningPath(pathId);
      setPath(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push("/login?redirect=/learn/" + pathId);
        return;
      }
      setError(err.response?.data?.detail || "Failed to load learning path");
    } finally {
      setLoading(false);
    }
  };

  const handlePauseResume = async () => {
    if (!path) return;
    
    setActionLoading(true);
    try {
      const newStatus = path.status === "active" ? "paused" : "active";
      await api.updateLearningPathStatus(pathId, newStatus);
      setPath({ ...path, status: newStatus });
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this learning path? This action cannot be undone.")) {
      return;
    }
    
    setActionLoading(true);
    try {
      await api.deleteLearningPath(pathId);
      router.push("/learn");
    } catch (err) {
      console.error("Failed to delete path:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: path?.title,
          text: `Check out my learning path: ${path?.title}`,
          url: window.location.href,
        });
      } catch (err) {
        console.log("Share cancelled");
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(window.location.href);
      alert("Link copied to clipboard!");
    }
  };

  // Find the current/next lesson to work on
  const currentLesson = path?.lessons?.find((l) => !l.is_completed && !l.is_locked);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (error || !path) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {error || "Learning path not found"}
        </h1>
        <Link
          href="/learn"
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          Back to My Learning Paths
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Link */}
      <Link
        href="/learn"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to My Learning Paths
      </Link>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-8">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-sm font-medium ${
                path.status === "active" 
                  ? "bg-green-100 text-green-700" 
                  : path.status === "completed"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-yellow-100 text-yellow-700"
              }`}>
                {path.status === "active" && <Play className="w-3.5 h-3.5" />}
                {path.status === "completed" && <CheckCircle2 className="w-3.5 h-3.5" />}
                {path.status === "paused" && <Pause className="w-3.5 h-3.5" />}
                {path.status.charAt(0).toUpperCase() + path.status.slice(1)}
              </span>
              <span className="text-sm text-gray-500">{path.target_skill}</span>
            </div>
            
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
              {path.title}
            </h1>
            
            {path.description && (
              <p className="text-gray-600">{path.description}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleShare}
              className="p-2 rounded-lg border border-gray-300 text-gray-600 
                       hover:bg-gray-50 transition-colors"
              title="Share"
            >
              <Share2 className="w-5 h-5" />
            </button>
            
            {path.status !== "completed" && (
              <button
                onClick={handlePauseResume}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border 
                         border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {path.status === "active" ? (
                  <>
                    <Pause className="w-4 h-4" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Resume
                  </>
                )}
              </button>
            )}
            
            <button
              onClick={handleDelete}
              disabled={actionLoading}
              className="p-2 rounded-lg border border-red-300 text-red-600 
                       hover:bg-red-50 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Quick Continue */}
        {currentLesson && path.status === "active" && (
          <div className="mt-6 pt-6 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-500 mb-1">Continue where you left off</div>
                <div className="font-medium text-gray-900">
                  Lesson {currentLesson.order}: {currentLesson.title}
                </div>
              </div>
              <Link
                href={`/learn/${pathId}/lesson/${currentLesson.id}`}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 
                         text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Play className="w-4 h-4" />
                Continue Learning
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Lessons List */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Lessons ({path.lessons?.length || 0})
          </h2>
          <div className="space-y-3">
            {path.lessons?.map((lesson) => (
              <LessonItem
                key={lesson.id}
                lesson={lesson}
                pathId={pathId}
                isActive={currentLesson?.id === lesson.id}
              />
            ))}
          </div>
        </div>

        {/* Progress Sidebar */}
        <div className="lg:col-span-1">
          <div className="sticky top-24">
            <PathProgress path={path} />
          </div>
        </div>
      </div>
    </div>
  );
}
