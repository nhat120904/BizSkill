"use client";

import { Target, Clock, TrendingUp, ChevronRight, BookOpen } from "lucide-react";
import type { LearningPath } from "@/types";

interface PathProgressProps {
  path: LearningPath;
}

export function PathProgress({ path }: PathProgressProps) {
  const progressPercent = Math.round(path.progress_percentage || 0);
  const remainingLessons = path.total_lessons - path.completed_lessons;
  
  // Estimate remaining time (rough calculation)
  const avgMinutesPerLesson = path.estimated_hours ? (path.estimated_hours * 60) / path.total_lessons : 10;
  const remainingMinutes = remainingLessons * avgMinutesPerLesson;
  const remainingHours = Math.round(remainingMinutes / 60 * 10) / 10;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Progress Circle */}
      <div className="flex items-center gap-6">
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="42"
              stroke="#E5E7EB"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="48"
              cy="48"
              r="42"
              stroke="#4F46E5"
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 42}`}
              strokeDashoffset={`${2 * Math.PI * 42 * (1 - progressPercent / 100)}`}
              className="transition-all duration-1000"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-gray-900">{progressPercent}%</span>
          </div>
        </div>

        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Your Progress</h3>
          <p className="text-sm text-gray-600">
            {path.completed_lessons} of {path.total_lessons} lessons completed
          </p>
          
          {/* Progress Bar */}
          <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-primary-500 to-primary-600 rounded-full transition-all duration-1000"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-100">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg mb-2">
            <BookOpen className="w-5 h-5 text-green-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900">{path.completed_lessons}</div>
          <div className="text-xs text-gray-500">Completed</div>
        </div>

        <div className="text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg mb-2">
            <Target className="w-5 h-5 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900">{remainingLessons}</div>
          <div className="text-xs text-gray-500">Remaining</div>
        </div>

        <div className="text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg mb-2">
            <Clock className="w-5 h-5 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900">{remainingHours}h</div>
          <div className="text-xs text-gray-500">Est. Left</div>
        </div>
      </div>

      {/* Learning Objectives */}
      {path.learning_objectives && path.learning_objectives.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Learning Objectives</h4>
          <ul className="space-y-2">
            {path.learning_objectives.map((objective, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <TrendingUp className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
                <span>{objective}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Skill Gap Analysis */}
      {path.skill_gap_analysis && (
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-900 mb-2">AI Analysis</h4>
          <p className="text-sm text-gray-600">{path.skill_gap_analysis}</p>
        </div>
      )}
    </div>
  );
}
