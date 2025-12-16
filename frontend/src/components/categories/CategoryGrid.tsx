"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Category } from "@/types";

export function CategoryGrid() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCategories()
      .then((data) => setCategories(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="animate-pulse rounded-xl bg-gray-200 h-28" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {categories.map((category) => (
        <Link
          key={category.slug}
          href={`/categories/${category.slug}`}
          className="group relative overflow-hidden rounded-xl bg-white border border-gray-100 p-6 hover:shadow-lg transition-all duration-200"
        >
          <div
            className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity"
            style={{ backgroundColor: category.color || '#005eff' }}
          />
          <div className="relative">
            <span className="text-3xl mb-3 block">{category.icon || '📚'}</span>
            <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
              {category.name}
            </h3>
            {category.segment_count !== undefined && category.segment_count > 0 && (
              <p className="text-sm text-gray-500 mt-1">{category.segment_count} clips</p>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
