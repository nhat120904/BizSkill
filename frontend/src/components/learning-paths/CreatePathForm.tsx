"use client";

import { useState } from "react";
import { Target, Clock, TrendingUp, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { LearningPathCreateRequest, SkillGapAnalysis } from "@/types";

interface CreatePathFormProps {
  onSuccess?: (pathId: string) => void;
  onCancel?: () => void;
  prefilledSkill?: string;
}

const LEVEL_OPTIONS = [
  { value: 1, label: "Beginner", description: "New to this skill" },
  { value: 2, label: "Elementary", description: "Basic understanding" },
  { value: 3, label: "Intermediate", description: "Can apply in practice" },
  { value: 4, label: "Advanced", description: "Strong proficiency" },
  { value: 5, label: "Expert", description: "Master level" },
];

export function CreatePathForm({ onSuccess, onCancel, prefilledSkill }: CreatePathFormProps) {
  const [step, setStep] = useState<"form" | "preview" | "creating">("form");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skillGap, setSkillGap] = useState<SkillGapAnalysis | null>(null);

  const [formData, setFormData] = useState<LearningPathCreateRequest>({
    target_skill: prefilledSkill || "",
    current_level: 1,
    target_level: 4,
    goals: "",
    time_commitment_hours: 5,
  });

  const handleAnalyze = async () => {
    if (!formData.target_skill.trim()) {
      setError("Please enter a skill to learn");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const analysis = await api.analyzeSkillGap(formData);
      setSkillGap(analysis);
      setStep("preview");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to analyze skill gap");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    setStep("creating");
    setIsLoading(true);
    setError(null);

    try {
      const path = await api.createLearningPath(formData);
      onSuccess?.(path.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create learning path");
      setStep("preview");
    } finally {
      setIsLoading(false);
    }
  };

  if (step === "creating") {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="relative">
          <Loader2 className="w-16 h-16 text-primary-600 animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Target className="w-6 h-6 text-primary-600" />
          </div>
        </div>
        <h3 className="mt-6 text-xl font-semibold text-gray-900">
          Creating Your Learning Path
        </h3>
        <p className="mt-2 text-gray-600 text-center max-w-md">
          Our AI agent is analyzing content and crafting the perfect learning journey for you...
        </p>
        <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
          <div className="w-2 h-2 bg-primary-600 rounded-full animate-pulse" />
          This may take 30-60 seconds
        </div>
      </div>
    );
  }

  if (step === "preview" && skillGap) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Skill Gap Analysis
          </h3>
          <p className="text-gray-600">{skillGap.gap_description}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Current Level</div>
            <div className="font-medium text-gray-900">{skillGap.current_level}</div>
          </div>
          <div className="bg-primary-50 rounded-lg p-4">
            <div className="text-sm text-primary-600 mb-1">Target Level</div>
            <div className="font-medium text-primary-900">{skillGap.target_level}</div>
          </div>
        </div>

        <div>
          <h4 className="font-medium text-gray-900 mb-2">Key Areas to Improve</h4>
          <ul className="space-y-2">
            {skillGap.key_areas_to_improve.map((area, i) => (
              <li key={i} className="flex items-start gap-2">
                <TrendingUp className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{area}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-1">Recommended Approach</h4>
          <p className="text-blue-800 text-sm">{skillGap.recommended_approach}</p>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>~{skillGap.estimated_learning_hours} hours</span>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-4">
          <button
            onClick={() => setStep("form")}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg 
                     hover:bg-gray-50 transition-colors"
          >
            Back
          </button>
          <button
            onClick={handleCreate}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg 
                     hover:bg-primary-700 transition-colors disabled:opacity-50
                     flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Learning Path"
            )}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Skill Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What skill do you want to learn?
        </label>
        <input
          type="text"
          value={formData.target_skill}
          onChange={(e) => setFormData({ ...formData, target_skill: e.target.value })}
          placeholder="e.g., Leadership, Negotiation, Public Speaking"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 
                   focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      {/* Current Level */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Your current level
        </label>
        <div className="grid grid-cols-5 gap-2">
          {LEVEL_OPTIONS.map((level) => (
            <button
              key={level.value}
              onClick={() => setFormData({ ...formData, current_level: level.value })}
              className={`p-3 rounded-lg border text-center transition-all ${
                formData.current_level === level.value
                  ? "border-primary-600 bg-primary-50 text-primary-700"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="font-medium text-sm">{level.label}</div>
              <div className="text-xs text-gray-500 mt-1 hidden sm:block">
                {level.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Target Level */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Target level
        </label>
        <div className="grid grid-cols-5 gap-2">
          {LEVEL_OPTIONS.filter((l) => l.value > formData.current_level).map((level) => (
            <button
              key={level.value}
              onClick={() => setFormData({ ...formData, target_level: level.value })}
              className={`p-3 rounded-lg border text-center transition-all ${
                formData.target_level === level.value
                  ? "border-primary-600 bg-primary-50 text-primary-700"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="font-medium text-sm">{level.label}</div>
              <div className="text-xs text-gray-500 mt-1 hidden sm:block">
                {level.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Goals (Optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Your learning goals (optional)
        </label>
        <textarea
          value={formData.goals || ""}
          onChange={(e) => setFormData({ ...formData, goals: e.target.value })}
          placeholder="e.g., I want to lead a team of 10 people effectively..."
          rows={3}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 
                   focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      {/* Time Commitment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Weekly time commitment: {formData.time_commitment_hours} hours
        </label>
        <input
          type="range"
          min="1"
          max="20"
          step="0.5"
          value={formData.time_commitment_hours}
          onChange={(e) =>
            setFormData({ ...formData, time_commitment_hours: parseFloat(e.target.value) })
          }
          className="w-full accent-primary-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1 hr/week</span>
          <span>20 hrs/week</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        {onCancel && (
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg 
                     hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleAnalyze}
          disabled={isLoading || !formData.target_skill.trim()}
          className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg 
                   hover:bg-primary-700 transition-colors disabled:opacity-50
                   flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Target className="w-4 h-4" />
              Analyze & Preview
            </>
          )}
        </button>
      </div>
    </div>
  );
}
