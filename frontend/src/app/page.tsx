import { SearchBar } from "@/components/search/SearchBar";
import { CategoryGrid } from "@/components/categories/CategoryGrid";
import { TrendingSegments } from "@/components/segments/TrendingSegments";
import { 
  Sparkles, 
  TrendingUp, 
  Clock, 
  Target 
} from "lucide-react";

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="py-16 md:py-24 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            AI-Powered Learning Platform
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Learn Business Skills in{" "}
            <span className="text-primary-600">Bite-Sized</span> Videos
          </h1>
          
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Stop watching hour-long videos. Get straight to the actionable insights 
            from the world&apos;s best business content creators.
          </p>
          
          {/* Search Bar */}
          <div className="max-w-2xl mx-auto mb-12">
            <SearchBar />
          </div>
          
          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-8 text-center">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary-600" />
              <span className="text-gray-700">
                <strong className="text-gray-900">1000+</strong> Segments
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary-600" />
              <span className="text-gray-700">
                <strong className="text-gray-900">2-5 min</strong> Each
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-primary-600" />
              <span className="text-gray-700">
                <strong className="text-gray-900">10</strong> Expert Channels
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-12 border-t border-gray-100">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Browse by Topic</h2>
          <a 
            href="/categories" 
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            View all →
          </a>
        </div>
        <CategoryGrid />
      </section>

      {/* Trending Section */}
      <section className="py-12 border-t border-gray-100">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Trending Insights</h2>
          <a 
            href="/feed" 
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            View all →
          </a>
        </div>
        <TrendingSegments />
      </section>

      {/* How It Works */}
      <section className="py-16 border-t border-gray-100">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">🎯</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Search Your Problem</h3>
            <p className="text-gray-600">
              Tell us what you want to learn. Our AI finds the exact video moments 
              that answer your question.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">✂️</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Watch Bite-Sized Clips</h3>
            <p className="text-gray-600">
              No more scrubbing through long videos. Watch just the 2-5 minute 
              segment that matters.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">🚀</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Apply & Grow</h3>
            <p className="text-gray-600">
              Each segment includes key takeaways. Save insights and build your 
              professional skills library.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-100 text-center text-gray-500 text-sm">
        <p>
          BizSkill AI curates content from trusted YouTube channels. 
          All videos play via the official YouTube player.
        </p>
        <p className="mt-2">
          © 2025 BizSkill AI. Built for busy professionals.
        </p>
      </footer>
    </div>
  );
}
