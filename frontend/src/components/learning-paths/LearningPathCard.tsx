"use client";

import Link from "next/link";
import { 
  BookOpen, Clock, CheckCircle2, PlayCircle, 
  Pause, MoreVertical, Trash2, TrendingUp 
} from "lucide-react";
import type { LearningPath } from "@/types";
import { useState, useRef, useEffect } from "react";

interface LearningPathCardProps {
  path: LearningPath;
  onDelete?: (pathId: string) => void;
  onPause?: (pathId: string) => void;
  onResume?: (pathId: string) => void;
}

function getStatusColor(status: string) {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-700";
    case "completed":
      return "bg-blue-100 text-blue-700";
    case "paused":
      return "bg-yellow-100 text-yellow-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "active":
      return <PlayCircle className="w-3.5 h-3.5" />;
    case "completed":
      return <CheckCircle2 className="w-3.5 h-3.5" />;
    case "paused":
      return <Pause className="w-3.5 h-3.5" />;
    default:
      return null;
  }
}

export function LearningPathCard({ path, onDelete, onPause, onResume }: LearningPathCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const progressPercent = Math.round(path.progress_percentage || 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="p-4 pb-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(path.status)}`}>
                {getStatusIcon(path.status)}
                {path.status.charAt(0).toUpperCase() + path.status.slice(1)}
              </span>
              <span className="text-xs text-gray-500">
                {path.target_skill}
              </span>
            </div>
            <Link href={`/learn/${path.id}`}>
              <h3 className="font-semibold text-gray-900 hover:text-primary-600 transition-colors line-clamp-2">
                {path.title}
              </h3>
            </Link>
          </div>
          
          {/* Menu */}
          <div className="relative" ref={menuRef}>
            <button 
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
            >
              <MoreVertical className="w-5 h-5 text-gray-400" />
            </button>
            
            {menuOpen && (
              <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                {path.status === "active" && onPause && (
                  <button
                    onClick={() => { onPause(path.id); setMenuOpen(false); }}
                    className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Pause className="w-4 h-4" />
                    Pause
                  </button>
                )}
                {path.status === "paused" && onResume && (
                  <button
                    onClick={() => { onResume(path.id); setMenuOpen(false); }}
                    className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <PlayCircle className="w-4 h-4" />
                    Resume
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => { onDelete(path.id); setMenuOpen(false); }}
                    className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
        
        {path.description && (
          <p className="text-sm text-gray-600 mt-2 line-clamp-2">
            {path.description}
          </p>
        )}
      </div>

      {/* Progress */}
      <div className="p-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600">
            {path.completed_lessons} of {path.total_lessons} lessons
          </span>
          <span className="font-medium text-primary-600">{progressPercent}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary-600 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          {path.estimated_hours && (
            <div className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>{path.estimated_hours}h total</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5" />
            <span>{path.total_lessons} lessons</span>
          </div>
        </div>
        
        <Link
          href={`/learn/${path.id}`}
          className="text-sm font-medium text-primary-600 hover:text-primary-700 flex items-center gap-1"
        >
          {path.status === "completed" ? "Review" : "Continue"}
          <TrendingUp className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
