"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  Plus, BookOpen, Target, TrendingUp, 
  Loader2, AlertCircle, Sparkles 
} from "lucide-react";
import { api } from "@/lib/api";
import { LearningPathCard, CreatePathModal } from "@/components/learning-paths";
import type { LearningPath, SuggestedSkill } from "@/types";

export default function LearnPage() {
  const router = useRouter();
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [suggestedSkills, setSuggestedSkills] = useState<SuggestedSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<string | undefined>();
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pathsData, skillsData] = await Promise.all([
        api.getLearningPaths(),
        api.getSuggestedSkills().catch(() => []),
      ]);
      setPaths(pathsData.paths);
      setSuggestedSkills(skillsData);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push("/login?redirect=/learn");
        return;
      }
      setError(err.response?.data?.detail || "Failed to load learning paths");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSuccess = (pathId: string) => {
    router.push(`/learn/${pathId}`);
  };

  const handleDelete = async (pathId: string) => {
    if (!confirm("Are you sure you want to delete this learning path?")) return;
    
    try {
      await api.deleteLearningPath(pathId);
      setPaths(paths.filter((p) => p.id !== pathId));
    } catch (err) {
      console.error("Failed to delete path:", err);
    }
  };

  const handlePause = async (pathId: string) => {
    try {
      await api.updateLearningPathStatus(pathId, "paused");
      setPaths(paths.map((p) => (p.id === pathId ? { ...p, status: "paused" as const } : p)));
    } catch (err) {
      console.error("Failed to pause path:", err);
    }
  };

  const handleResume = async (pathId: string) => {
    try {
      await api.updateLearningPathStatus(pathId, "active");
      setPaths(paths.map((p) => (p.id === pathId ? { ...p, status: "active" as const } : p)));
    } catch (err) {
      console.error("Failed to resume path:", err);
    }
  };

  const handleSkillClick = (skill: string) => {
    setSelectedSkill(skill);
    setShowCreateModal(true);
  };

  const filteredPaths = filter === "all" 
    ? paths 
    : paths.filter((p) => p.status === filter);

  const activePaths = paths.filter((p) => p.status === "active");
  const completedPaths = paths.filter((p) => p.status === "completed");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Target className="w-8 h-8 text-primary-600" />
            My Learning Paths
          </h1>
          <p className="mt-2 text-gray-600">
            AI-powered personalized learning journeys tailored to your goals
          </p>
        </div>
        <button
          onClick={() => { setSelectedSkill(undefined); setShowCreateModal(true); }}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white 
                   rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          <Plus className="w-5 h-5" />
          Create New Path
        </button>
      </div>

      {/* Stats */}
      {paths.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{paths.length}</div>
            <div className="text-sm text-gray-600">Total Paths</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-green-600">{activePaths.length}</div>
            <div className="text-sm text-gray-600">In Progress</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-blue-600">{completedPaths.length}</div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-purple-600">
              {paths.reduce((sum, p) => sum + p.completed_lessons, 0)}
            </div>
            <div className="text-sm text-gray-600">Lessons Learned</div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      {paths.length > 0 && (
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          {[
            { value: "all", label: "All" },
            { value: "active", label: "Active" },
            { value: "completed", label: "Completed" },
            { value: "paused", label: "Paused" },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                filter === tab.value
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 mb-6">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Empty State */}
      {paths.length === 0 && !loading && (
        <div className="text-center py-16">
          <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <BookOpen className="w-10 h-10 text-primary-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Start Your Learning Journey
          </h2>
          <p className="text-gray-600 max-w-md mx-auto mb-8">
            Create your first AI-powered learning path. Tell us what skill you want to master, 
            and we&apos;ll design a personalized curriculum for you.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white 
                     rounded-lg hover:bg-primary-700 transition-colors font-medium"
          >
            <Sparkles className="w-5 h-5" />
            Create Your First Path
          </button>
        </div>
      )}

      {/* Learning Paths Grid */}
      {filteredPaths.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {filteredPaths.map((path) => (
            <LearningPathCard
              key={path.id}
              path={path}
              onDelete={handleDelete}
              onPause={handlePause}
              onResume={handleResume}
            />
          ))}
        </div>
      )}

      {/* Suggested Skills */}
      {suggestedSkills.length > 0 && (
        <div className="mt-12">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            Suggested Skills to Learn
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {suggestedSkills.map((skill) => (
              <button
                key={skill.skill}
                onClick={() => handleSkillClick(skill.skill)}
                className="p-4 bg-white rounded-xl border border-gray-200 hover:border-primary-300 
                         hover:shadow-md transition-all text-left group"
              >
                <div className="flex items-center gap-2 mb-2">
                  {skill.icon && <span className="text-xl">{skill.icon}</span>}
                  <span className="font-medium text-gray-900 group-hover:text-primary-600">
                    {skill.skill}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  {skill.available_lessons} lessons available
                </div>
                {skill.is_interest && (
                  <span className="inline-block mt-2 px-2 py-0.5 bg-primary-100 text-primary-700 
                               text-xs rounded-full">
                    Matches your interests
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Create Path Modal */}
      <CreatePathModal
        isOpen={showCreateModal}
        onClose={() => { setShowCreateModal(false); setSelectedSkill(undefined); }}
        onSuccess={handleCreateSuccess}
        prefilledSkill={selectedSkill}
      />
    </div>
  );
}
