"use client";

import Link from "next/link";

const CATEGORIES = [
  { name: "Leadership", slug: "leadership", icon: "👑", color: "#FFD700" },
  { name: "Communication", slug: "communication", icon: "💬", color: "#4A90E2" },
  { name: "Sales", slug: "sales", icon: "💰", color: "#27AE60" },
  { name: "Marketing", slug: "marketing", icon: "📢", color: "#E74C3C" },
  { name: "Productivity", slug: "productivity", icon: "⚡", color: "#F39C12" },
  { name: "Career Growth", slug: "career-growth", icon: "📈", color: "#9B59B6" },
  { name: "Negotiation", slug: "negotiation", icon: "🤝", color: "#1ABC9C" },
  { name: "Entrepreneurship", slug: "entrepreneurship", icon: "🚀", color: "#E91E63" },
];

export function CategoryGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {CATEGORIES.map((category) => (
        <Link
          key={category.slug}
          href={`/categories/${category.slug}`}
          className="group relative overflow-hidden rounded-xl bg-white border border-gray-100 p-6 hover:shadow-lg transition-all duration-200"
        >
          <div
            className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity"
            style={{ backgroundColor: category.color }}
          />
          <div className="relative">
            <span className="text-3xl mb-3 block">{category.icon}</span>
            <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
              {category.name}
            </h3>
          </div>
        </Link>
      ))}
    </div>
  );
}
