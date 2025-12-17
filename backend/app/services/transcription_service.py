from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()

# Global model cache
_local_whisper_model = None


def get_local_whisper_model():
    """Lazy load local Whisper model"""
    global _local_whisper_model
    if _local_whisper_model is None:
        logger.info("Loading local Whisper model", 
                   model=settings.whisper_model,
                   device=settings.whisper_device)
        import whisper
        _local_whisper_model = whisper.load_model(
            settings.whisper_model,
            device=settings.whisper_device
        )
        logger.info("Local Whisper model loaded successfully")
    return _local_whisper_model


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
    """Service for transcribing audio using Whisper (local or OpenAI API)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.use_local = settings.use_local_whisper
        self.model_name = settings.whisper_model
        
        if not self.use_local:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key or settings.openai_api_key)
    
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio file using Whisper
        Returns full transcript with word-level timestamps
        """
        if self.use_local:
            return self._transcribe_local(audio_path)
        else:
            return self._transcribe_openai(audio_path)
    
    def _transcribe_local(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using local Whisper model"""
        logger.info("Starting local transcription", 
                   audio_path=str(audio_path),
                   model=self.model_name)
        
        try:
            model = get_local_whisper_model()
            
            # Transcribe with word-level timestamps
            result = model.transcribe(
                str(audio_path),
                word_timestamps=True,
                language=None,  # Auto-detect
                verbose=False
            )
            
            # Extract word timestamps from segments
            words = []
            if 'segments' in result:
                for segment in result['segments']:
                    if 'words' in segment:
                        for w in segment['words']:
                            words.append(WordTimestamp(
                                word=w.get('word', '').strip(),
                                start=w.get('start', 0),
                                end=w.get('end', 0)
                            ))
            
            # Calculate duration from last word or segments
            duration = 0
            if words:
                duration = words[-1].end
            elif result.get('segments'):
                duration = result['segments'][-1].get('end', 0)
            
            transcription_result = TranscriptionResult(
                full_text=result.get('text', '').strip(),
                words=words,
                language=result.get('language', 'en'),
                duration=duration
            )
            
            logger.info("Local transcription completed", 
                       word_count=len(words),
                       duration=transcription_result.duration,
                       language=transcription_result.language)
            
            return transcription_result
            
        except Exception as e:
            logger.error("Local transcription failed", 
                        audio_path=str(audio_path), 
                        error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def _transcribe_openai(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API"""
        logger.info("Starting OpenAI transcription", audio_path=str(audio_path))
        
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )
            
            # Extract word timestamps
            words = []
            if hasattr(response, 'words') and response.words:
                for w in response.words:
                    if hasattr(w, 'word'):
                        words.append(WordTimestamp(
                            word=getattr(w, 'word', getattr(w, 'text', '')),
                            start=getattr(w, 'start', 0),
                            end=getattr(w, 'end', 0)
                        ))
                    else:
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
            
            logger.info("OpenAI transcription completed", 
                       word_count=len(words),
                       duration=result.duration,
                       language=result.language)
            
            return result
            
        except Exception as e:
            logger.error("OpenAI transcription failed", 
                        audio_path=str(audio_path), 
                        error=str(e))
            raise
    
    def transcribe_with_segments(self, audio_path: Path) -> dict:
        """
        Transcribe with segment-level timestamps (for longer context)
        """
        if self.use_local:
            return self._transcribe_segments_local(audio_path)
        else:
            return self._transcribe_segments_openai(audio_path)
    
    def _transcribe_segments_local(self, audio_path: Path) -> dict:
        """Transcribe with segments using local model"""
        logger.info("Starting local segment transcription", audio_path=str(audio_path))
        
        model = get_local_whisper_model()
        result = model.transcribe(
            str(audio_path),
            word_timestamps=False,
            language=None,
            verbose=False
        )
        
        segments = []
        for i, seg in enumerate(result.get('segments', [])):
            segments.append({
                'id': i,
                'start': seg.get('start', 0),
                'end': seg.get('end', 0),
                'text': seg.get('text', '').strip(),
            })
        
        duration = segments[-1]['end'] if segments else 0
        
        return {
            'full_text': result.get('text', '').strip(),
            'segments': segments,
            'language': result.get('language', 'en'),
            'duration': duration
        }
    
    def _transcribe_segments_openai(self, audio_path: Path) -> dict:
        """Transcribe with segments using OpenAI API"""
        logger.info("Starting OpenAI segment transcription", audio_path=str(audio_path))
        
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                if hasattr(seg, 'id'):
                    segments.append({
                        'id': getattr(seg, 'id', 0),
                        'start': getattr(seg, 'start', 0),
                        'end': getattr(seg, 'end', 0),
                        'text': getattr(seg, 'text', ''),
                    })
                else:
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
