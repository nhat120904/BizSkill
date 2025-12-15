from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Optional, Dict, Any
from datetime import datetime
import isodate
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class YouTubeService:
    """Service for interacting with YouTube Data API v3"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.youtube_api_key
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Fetch channel metadata by channel ID"""
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            ).execute()
            
            if not response.get('items'):
                return None
            
            item = response['items'][0]
            return {
                'youtube_channel_id': item['id'],
                'name': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url'),
                'custom_url': item['snippet'].get('customUrl'),
                'subscriber_count': item['statistics'].get('subscriberCount'),
                'uploads_playlist_id': item['contentDetails']['relatedPlaylists']['uploads']
            }
        except HttpError as e:
            logger.error("YouTube API error", error=str(e), channel_id=channel_id)
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_channel_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        """Fetch channel by @handle"""
        try:
            # Remove @ if present
            handle = handle.lstrip('@')
            
            response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails',
                forHandle=handle
            ).execute()
            
            if not response.get('items'):
                return None
            
            item = response['items'][0]
            return {
                'youtube_channel_id': item['id'],
                'name': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url'),
                'custom_url': item['snippet'].get('customUrl'),
                'subscriber_count': item['statistics'].get('subscriberCount'),
                'uploads_playlist_id': item['contentDetails']['relatedPlaylists']['uploads']
            }
        except HttpError as e:
            logger.error("YouTube API error", error=str(e), handle=handle)
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_latest_videos(
        self, 
        uploads_playlist_id: str, 
        max_results: int = 50,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch latest videos from a channel's uploads playlist"""
        try:
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                response = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get('items', []):
                    published_at = datetime.fromisoformat(
                        item['snippet']['publishedAt'].replace('Z', '+00:00')
                    )
                    
                    # Stop if we've gone past the since date
                    if since and published_at < since:
                        return videos
                    
                    videos.append({
                        'youtube_id': item['contentDetails']['videoId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet'].get('description', ''),
                        'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url'),
                        'publish_date': published_at,
                    })
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            return videos
        except HttpError as e:
            logger.error("YouTube API error", error=str(e), playlist_id=uploads_playlist_id)
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Batch fetch video metadata (max 50 per request)"""
        try:
            videos = []
            
            # Process in batches of 50
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                
                response = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch)
                ).execute()
                
                for item in response.get('items', []):
                    duration = isodate.parse_duration(item['contentDetails']['duration'])
                    
                    videos.append({
                        'youtube_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet'].get('description', ''),
                        'channel_id': item['snippet']['channelId'],
                        'channel_name': item['snippet']['channelTitle'],
                        'thumbnail_url': item['snippet']['thumbnails'].get('maxres', 
                            item['snippet']['thumbnails'].get('high', {})).get('url'),
                        'publish_date': datetime.fromisoformat(
                            item['snippet']['publishedAt'].replace('Z', '+00:00')
                        ),
                        'duration_seconds': int(duration.total_seconds()),
                        'view_count': item['statistics'].get('viewCount'),
                    })
            
            return videos
        except HttpError as e:
            logger.error("YouTube API error", error=str(e), video_ids=video_ids[:5])
            raise
    
    def check_video_exists(self, video_id: str) -> bool:
        """Check if a video is still available"""
        try:
            response = self.youtube.videos().list(
                part='id',
                id=video_id
            ).execute()
            return len(response.get('items', [])) > 0
        except HttpError:
            return False
