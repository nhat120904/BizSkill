"use client";

import { useEffect, useState } from "react";
import { SegmentCard } from "./SegmentCard";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Segment } from "@/types";

export function TrendingSegments() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTrending() {
      try {
        const response = await api.getFeed("trending", 1, 8);
        setSegments(response.results);
      } catch (err) {
        setError("Failed to load trending segments");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchTrending();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 text-primary-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No segments available yet. Check back soon!</p>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {segments.map((segment) => (
        <SegmentCard key={segment.id} segment={segment} />
      ))}
    </div>
  );
}
