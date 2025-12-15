"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, Loader2 } from "lucide-react";

interface SearchBarProps {
  initialQuery?: string;
  size?: "default" | "large";
  autoFocus?: boolean;
}

export function SearchBar({ 
  initialQuery = "", 
  size = "large",
  autoFocus = false 
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (query.trim()) {
        setIsLoading(true);
        router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      }
    },
    [query, router]
  );

  const clearQuery = () => {
    setQuery("");
  };

  const sizeClasses = {
    default: "h-12 text-base",
    large: "h-14 text-lg",
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for skills... (e.g., 'how to negotiate salary')"
          autoFocus={autoFocus}
          className={`
            w-full ${sizeClasses[size]} pl-12 pr-24 
            bg-white border border-gray-200 rounded-xl
            text-gray-900 placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
            shadow-sm hover:shadow-md transition-shadow
          `}
        />
        
        {query && (
          <button
            type="button"
            onClick={clearQuery}
            className="absolute right-20 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className={`
            absolute right-2 top-1/2 -translate-y-1/2
            px-4 py-2 bg-primary-600 text-white rounded-lg
            font-medium text-sm
            hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          `}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </div>
      
      {/* Quick suggestions */}
      <div className="flex flex-wrap gap-2 mt-4 justify-center">
        {["leadership tips", "time management", "negotiation skills", "public speaking"].map(
          (suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setQuery(suggestion);
                router.push(`/search?q=${encodeURIComponent(suggestion)}`);
              }}
              className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors"
            >
              {suggestion}
            </button>
          )
        )}
      </div>
    </form>
  );
}
