"use client";

import { useState } from "react";
import { X, Sparkles } from "lucide-react";
import { CreatePathForm } from "./CreatePathForm";

interface CreatePathModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (pathId: string) => void;
  prefilledSkill?: string;
}

export function CreatePathModal({ isOpen, onClose, onSuccess, prefilledSkill }: CreatePathModalProps) {
  if (!isOpen) return null;

  const handleSuccess = (pathId: string) => {
    onSuccess?.(pathId);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Create Learning Path
                </h2>
                <p className="text-sm text-gray-500">
                  Let AI craft your personalized journey
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Form */}
          <div className="p-6">
            <CreatePathForm 
              onSuccess={handleSuccess}
              onCancel={onClose}
              prefilledSkill={prefilledSkill}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
