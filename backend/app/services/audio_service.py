import os
import tempfile
from pathlib import Path
from typing import Optional
import yt_dlp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class AudioExtractionService:
    """Service for downloading audio from YouTube videos"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir or settings.temp_audio_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def download_audio(self, youtube_id: str) -> Path:
        """
        Download audio track only from YouTube video
        Returns path to the downloaded audio file
        """
        output_path = self.temp_dir / f"{youtube_id}"
        final_path = self.temp_dir / f"{youtube_id}.mp3"
        
        # If already downloaded, return existing file
        if final_path.exists():
            logger.info("Audio already downloaded", youtube_id=youtube_id)
            return final_path
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
            # Rate limiting to be nice to YouTube
            'sleep_interval': 1,
            'max_sleep_interval': 3,
        }
        
        url = f"https://www.youtube.com/watch?v={youtube_id}"
        
        try:
            logger.info("Downloading audio", youtube_id=youtube_id)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not final_path.exists():
                # Check for other formats
                for ext in ['.mp3', '.m4a', '.opus', '.webm']:
                    alt_path = self.temp_dir / f"{youtube_id}{ext}"
                    if alt_path.exists():
                        alt_path.rename(final_path)
                        break
            
            if not final_path.exists():
                raise FileNotFoundError(f"Audio file not found after download: {youtube_id}")
            
            logger.info("Audio downloaded successfully", 
                       youtube_id=youtube_id, 
                       size_mb=round(final_path.stat().st_size / (1024*1024), 2))
            
            return final_path
            
        except Exception as e:
            logger.error("Failed to download audio", youtube_id=youtube_id, error=str(e))
            raise
    
    def cleanup(self, file_path: Path) -> None:
        """Securely delete audio file after processing"""
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.info("Cleaned up audio file", path=str(file_path))
        except Exception as e:
            logger.warning("Failed to cleanup audio file", path=str(file_path), error=str(e))
    
    def cleanup_all(self, youtube_id: str) -> None:
        """Clean up all files related to a video"""
        for ext in ['.mp3', '.m4a', '.opus', '.webm', '.part', '.ytdl']:
            file_path = self.temp_dir / f"{youtube_id}{ext}"
            self.cleanup(file_path)
    
    def get_temp_dir_size(self) -> int:
        """Get total size of temp directory in bytes"""
        total = 0
        for f in self.temp_dir.glob('*'):
            if f.is_file():
                total += f.stat().st_size
        return total
