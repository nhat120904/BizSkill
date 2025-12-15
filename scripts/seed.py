#!/usr/bin/env python3
"""
Seed script to initialize BizSkill with 10 famous business channels
and trigger video processing to create ~1000 short segments.
"""

import asyncio
import httpx
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

# 10 Famous Business YouTube Channels
SEED_CHANNELS = [
    {
        "youtube_channel_id": "UCAuUUnT6oDeKwE6v1US8Lrw",
        "name": "TED",
        "description": "TED Talks share ideas worth spreading across technology, entertainment, and design.",
    },
    {
        "youtube_channel_id": "UCEvWr0LGQE6tE83bCFvUvMQ",
        "name": "Harvard Business Review",
        "description": "Management tips, leadership advice, and business strategy from HBR.",
    },
    {
        "youtube_channel_id": "UCxIJaCMEptJjxmmQgGFsnCg",
        "name": "Y Combinator",
        "description": "Startup advice from the world's most successful accelerator.",
    },
    {
        "youtube_channel_id": "UCCtlgoQBJIpIaVl9WVVMJqw",
        "name": "GaryVee",
        "description": "Gary Vaynerchuk on entrepreneurship, marketing, and social media.",
    },
    {
        "youtube_channel_id": "UCDXJazlG6n8dB6NagN2gPbg",
        "name": "Simon Sinek",
        "description": "Leadership, inspiration, and finding your 'Why'.",
    },
    {
        "youtube_channel_id": "UCbxb2fqe9oNgglAoYqsYOtQ",
        "name": "The Futur",
        "description": "Business of design, pricing, and creative entrepreneurship.",
    },
    {
        "youtube_channel_id": "UCIHdDJ0tjn_3j-FS7s_X1kQ",
        "name": "Valuetainment",
        "description": "Patrick Bet-David on business, politics, and entrepreneurship.",
    },
    {
        "youtube_channel_id": "UCoOae5nYA7VqaXzerajD0lg",
        "name": "Ali Abdaal",
        "description": "Productivity, business, and working smarter.",
    },
    {
        "youtube_channel_id": "UC88tlMjiS7kf8uhPWyBTn_A",
        "name": "MasterClass",
        "description": "Learn from the world's best in business and beyond.",
    },
    {
        "youtube_channel_id": "UCSiOQS0K1XM_IB9RZhMuxzQ",
        "name": "Stanford Graduate School of Business",
        "description": "World-class business education and insights.",
    },
]

# Categories to seed
SEED_CATEGORIES = [
    {"name": "Leadership", "slug": "leadership", "icon": "👔", "color": "#3B82F6"},
    {"name": "Marketing", "slug": "marketing", "icon": "📢", "color": "#10B981"},
    {"name": "Startups", "slug": "startups", "icon": "🚀", "color": "#F59E0B"},
    {"name": "Finance", "slug": "finance", "icon": "💰", "color": "#6366F1"},
    {"name": "Productivity", "slug": "productivity", "icon": "⚡", "color": "#EC4899"},
    {"name": "Communication", "slug": "communication", "icon": "💬", "color": "#8B5CF6"},
    {"name": "Negotiation", "slug": "negotiation", "icon": "🤝", "color": "#14B8A6"},
    {"name": "Innovation", "slug": "innovation", "icon": "💡", "color": "#F97316"},
]


async def wait_for_api(client: httpx.AsyncClient, max_retries: int = 30) -> bool:
    """Wait for the API to be ready."""
    for i in range(max_retries):
        try:
            response = await client.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
            if response.status_code == 200:
                print("✅ API is ready!")
                return True
        except Exception:
            pass
        print(f"⏳ Waiting for API... ({i + 1}/{max_retries})")
        await asyncio.sleep(2)
    return False


async def initialize_platform(client: httpx.AsyncClient) -> bool:
    """Initialize the platform with channels and categories."""
    print("\n🚀 Initializing platform...")
    
    try:
        response = await client.post(
            f"{API_BASE_URL}/admin/init",
            json={
                "channels": SEED_CHANNELS,
                "categories": SEED_CATEGORIES,
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ {data['message']}")
            print(f"     Channels: {', '.join(data['channels'])}")
            print(f"     Categories: {', '.join(data['categories'])}")
            return True
        elif response.status_code == 400:
            data = response.json()
            print(f"  ⚠️  {data.get('detail', 'Platform already initialized')}")
            return True  # Already initialized is OK
        else:
            print(f"  ❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("🎯 BizSkill Seed Script")
    print(f"   Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Wait for API
        if not await wait_for_api(client):
            print("❌ API is not available. Please start the services first.")
            return
        
        # Initialize platform
        success = await initialize_platform(client)
        
        if not success:
            print("\n❌ Initialization failed. Exiting.")
            return
        
        print("\n" + "=" * 60)
        print("🚀 Seed complete!")
        print("")
        print("Next steps:")
        print("  1. Videos will be downloaded and processed as you add them")
        print("  2. Use the admin API to sync channels: POST /api/v1/admin/channels/{id}/sync")
        print("  3. Monitor progress at: http://localhost:5555 (Flower)")
        print("  4. View the app at: http://localhost:3000")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
