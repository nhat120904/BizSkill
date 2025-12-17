"""
Video Clip Service - Download, cut and upload video segments to Cloudinary
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
import cloudinary
import cloudinary.uploader
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class VideoClipService:
    """Service for downloading, cutting and uploading video segments"""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_video_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def download_video(self, youtube_id: str) -> Path:
        """
        Download video from YouTube
        Returns path to downloaded video file
        """
        output_path = self.temp_dir / f"{youtube_id}"
        final_path = self.temp_dir / f"{youtube_id}.mp4"
        
        # If already downloaded, return existing file
        if final_path.exists():
            logger.info("Video already downloaded", youtube_id=youtube_id)
            return final_path
        
        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'sleep_interval': 1,
            'max_sleep_interval': 3,
        }
        
        url = f"https://www.youtube.com/watch?v={youtube_id}"
        
        try:
            logger.info("Downloading video", youtube_id=youtube_id)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Check for the output file
            if not final_path.exists():
                # Check for other extensions
                for ext in ['.mp4', '.mkv', '.webm']:
                    alt_path = self.temp_dir / f"{youtube_id}{ext}"
                    if alt_path.exists():
                        if ext != '.mp4':
                            # Convert to mp4
                            self._convert_to_mp4(alt_path, final_path)
                            os.remove(alt_path)
                        else:
                            alt_path.rename(final_path)
                        break
            
            if not final_path.exists():
                raise FileNotFoundError(f"Video file not found after download: {youtube_id}")
            
            logger.info("Video downloaded successfully", 
                       youtube_id=youtube_id, 
                       size_mb=round(final_path.stat().st_size / (1024*1024), 2))
            
            return final_path
            
        except Exception as e:
            logger.error("Failed to download video", youtube_id=youtube_id, error=str(e))
            raise
    
    def _convert_to_mp4(self, input_path: Path, output_path: Path):
        """Convert video to MP4 using ffmpeg"""
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    def cut_segment(
        self, 
        video_path: Path, 
        start_time: float, 
        end_time: float,
        segment_id: str
    ) -> Path:
        """
        Cut a segment from video using ffmpeg
        Returns path to the cut segment
        """
        output_path = self.temp_dir / f"segment_{segment_id}.mp4"
        
        duration = end_time - start_time
        
        # Use ffmpeg to cut the video
        # Using -ss before -i for fast seeking
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),
            '-i', str(video_path),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',  # Enable streaming
            '-avoid_negative_ts', 'make_zero',
            str(output_path)
        ]
        
        try:
            logger.info("Cutting segment", 
                       segment_id=segment_id, 
                       start=start_time, 
                       end=end_time)
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if not output_path.exists():
                raise FileNotFoundError(f"Segment file not created: {segment_id}")
            
            logger.info("Segment cut successfully",
                       segment_id=segment_id,
                       size_mb=round(output_path.stat().st_size / (1024*1024), 2))
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error("FFmpeg error", 
                        segment_id=segment_id, 
                        stderr=e.stderr)
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def upload_to_cloudinary(
        self, 
        video_path: Path, 
        segment_id: str,
        title: str,
        tags: list = None
    ) -> Dict[str, Any]:
        """
        Upload video segment to Cloudinary
        Returns Cloudinary response with URLs
        """
        public_id = f"{settings.cloudinary_folder}/{segment_id}"
        
        try:
            logger.info("Uploading to Cloudinary", segment_id=segment_id)
            
            response = cloudinary.uploader.upload(
                str(video_path),
                resource_type="video",
                public_id=public_id,
                overwrite=True,
                tags=tags or [],
                context={
                    "title": title,
                    "segment_id": segment_id
                },
                # Optimization options
                eager=[
                    # Create different quality versions
                    {"format": "mp4", "quality": "auto"},
                    {"format": "webm", "quality": "auto"},
                    # Create thumbnail
                    {"format": "jpg", "transformation": [
                        {"width": 480, "height": 270, "crop": "fill"},
                        {"start_offset": "0"}
                    ]},
                ],
                eager_async=True,
            )
            
            logger.info("Upload successful", 
                       segment_id=segment_id,
                       url=response.get('secure_url'))
            
            return {
                "public_id": response.get("public_id"),
                "url": response.get("secure_url"),
                "playback_url": response.get("secure_url"),
                "thumbnail_url": response.get("secure_url").replace(".mp4", ".jpg"),
                "duration": response.get("duration"),
                "format": response.get("format"),
                "width": response.get("width"),
                "height": response.get("height"),
                "bytes": response.get("bytes"),
            }
            
        except Exception as e:
            logger.error("Cloudinary upload failed", 
                        segment_id=segment_id, 
                        error=str(e))
            raise
    
    def process_segment(
        self,
        youtube_id: str,
        segment_id: str,
        start_time: float,
        end_time: float,
        title: str,
        categories: list = None
    ) -> Dict[str, Any]:
        """
        Full pipeline: download video, cut segment, upload to Cloudinary
        Returns Cloudinary URLs
        """
        try:
            # 1. Download full video (cached if exists)
            video_path = self.download_video(youtube_id)
            
            # 2. Cut the segment
            segment_path = self.cut_segment(
                video_path, 
                start_time, 
                end_time, 
                segment_id
            )
            
            # 3. Upload to Cloudinary
            result = self.upload_to_cloudinary(
                segment_path,
                segment_id,
                title,
                tags=categories
            )
            
            # 4. Cleanup segment file
            self.cleanup(segment_path)
            
            return result
            
        except Exception as e:
            logger.error("Segment processing failed",
                        youtube_id=youtube_id,
                        segment_id=segment_id,
                        error=str(e))
            raise
    
    def cleanup(self, file_path: Path) -> None:
        """Delete a file"""
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.info("Cleaned up file", path=str(file_path))
        except Exception as e:
            logger.warning("Failed to cleanup file", path=str(file_path), error=str(e))
    
    def cleanup_video(self, youtube_id: str) -> None:
        """Clean up downloaded video file"""
        for ext in ['.mp4', '.mkv', '.webm', '.part', '.ytdl']:
            file_path = self.temp_dir / f"{youtube_id}{ext}"
            self.cleanup(file_path)
    
    def get_temp_dir_size(self) -> int:
        """Get total size of temp directory in bytes"""
        total = 0
        if self.temp_dir.exists():
            for f in self.temp_dir.glob('*'):
                if f.is_file():
                    total += f.stat().st_size
        return total
