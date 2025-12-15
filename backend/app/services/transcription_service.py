from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptionResult(BaseModel):
    full_text: str
    words: List[WordTimestamp]
    language: str
    duration: float


class TranscriptionService:
    """Service for transcribing audio using OpenAI Whisper"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.whisper_model
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio file using Whisper
        Returns full transcript with word-level timestamps
        """
        logger.info("Starting transcription", audio_path=str(audio_path))
        
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )
            
            # Extract word timestamps
            words = []
            if hasattr(response, 'words') and response.words:
                for w in response.words:
                    # Handle both dict and object attributes (SDK version compatibility)
                    if hasattr(w, 'word'):
                        # Newer SDK: word is an object
                        words.append(WordTimestamp(
                            word=getattr(w, 'word', getattr(w, 'text', '')),
                            start=getattr(w, 'start', 0),
                            end=getattr(w, 'end', 0)
                        ))
                    else:
                        # Older SDK: word is a dict
                        words.append(WordTimestamp(
                            word=w.get('word', w.get('text', '')),
                            start=w.get('start', 0),
                            end=w.get('end', 0)
                        ))
            
            result = TranscriptionResult(
                full_text=response.text,
                words=words,
                language=getattr(response, 'language', 'en'),
                duration=getattr(response, 'duration', 0)
            )
            
            logger.info("Transcription completed", 
                       word_count=len(words),
                       duration=result.duration,
                       language=result.language)
            
            return result
            
        except Exception as e:
            logger.error("Transcription failed", audio_path=str(audio_path), error=str(e))
            raise
    
    def transcribe_with_segments(self, audio_path: Path) -> dict:
        """
        Transcribe with segment-level timestamps (for longer context)
        """
        logger.info("Starting segment transcription", audio_path=str(audio_path))
        
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                # Handle both dict and object attributes (SDK version compatibility)
                if hasattr(seg, 'id'):
                    # Newer SDK: segment is an object
                    segments.append({
                        'id': getattr(seg, 'id', 0),
                        'start': getattr(seg, 'start', 0),
                        'end': getattr(seg, 'end', 0),
                        'text': getattr(seg, 'text', ''),
                    })
                else:
                    # Older SDK: segment is a dict
                    segments.append({
                        'id': seg.get('id', 0),
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', ''),
                    })
        
        return {
            'full_text': response.text,
            'segments': segments,
            'language': getattr(response, 'language', 'en'),
            'duration': getattr(response, 'duration', 0)
        }
