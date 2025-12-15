import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class SegmentInfo(BaseModel):
    start_time: int  # seconds
    end_time: int    # seconds
    topic: str
    context: str


class InsightResult(BaseModel):
    generated_title: str
    summary_text: str
    key_takeaways: List[str]
    relevance_score: int  # 1-10
    categories: List[str]


SEGMENTATION_SYSTEM_PROMPT = """You are an expert content analyst specializing in business and professional development content.
Your task is to analyze video transcripts and identify distinct, self-contained learning segments.

RULES:
1. Each segment MUST be a complete, standalone lesson or insight (minimum 60 seconds, maximum 5 minutes)
2. Segments should have clear beginning and ending points - never cut mid-sentence
3. Identify natural topic transitions in the content
4. Focus on ACTIONABLE advice segments
5. Skip intros, outros, sponsor reads, and off-topic tangents
6. Aim for 3-10 segments per 30 minutes of content
7. Add ±2 seconds buffer to timestamps to avoid cutting mid-word

You will receive transcript with timestamps. Return valid JSON only."""


INSIGHT_SYSTEM_PROMPT = """You are an expert content marketer creating engaging short-form content from business videos.
Generate compelling titles, summaries, and takeaways that would make professionals want to watch.

RULES:
1. Titles should be catchy but professional (max 60 chars)
2. Use numbers when appropriate (e.g., "3 Steps to...")
3. Include power words (Master, Essential, Secret, Proven, etc.)
4. Key takeaways must be actionable and specific
5. Be accurate - don't oversell or exaggerate the content

Return valid JSON only."""


class LLMSegmentationService:
    """Service for AI-powered video segmentation and insight extraction"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.llm_model
    
    def _chunk_transcript(self, transcript_segments: List[dict], max_duration: int = 600) -> List[List[dict]]:
        """Split transcript into processable chunks (~10 min each)"""
        chunks = []
        current_chunk = []
        current_duration = 0
        
        for seg in transcript_segments:
            seg_duration = seg['end'] - seg['start']
            
            if current_duration + seg_duration > max_duration and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_duration = 0
            
            current_chunk.append(seg)
            current_duration += seg_duration
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _format_transcript_for_llm(self, segments: List[dict]) -> str:
        """Format transcript segments with timestamps for LLM input"""
        lines = []
        for seg in segments:
            start = int(seg['start'])
            end = int(seg['end'])
            text = seg['text'].strip()
            lines.append(f"[{start}s - {end}s]: {text}")
        return "\n".join(lines)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def identify_segments(
        self, 
        transcript_segments: List[dict],
        video_title: str,
        video_duration: int
    ) -> List[SegmentInfo]:
        """
        Use LLM to identify logical segments within the transcript
        """
        logger.info("Starting segment identification", 
                   video_title=video_title,
                   transcript_segments=len(transcript_segments))
        
        all_segments = []
        chunks = self._chunk_transcript(transcript_segments)
        
        for i, chunk in enumerate(chunks):
            chunk_start = int(chunk[0]['start'])
            chunk_end = int(chunk[-1]['end'])
            
            formatted_transcript = self._format_transcript_for_llm(chunk)
            
            prompt = f"""Analyze this transcript chunk from the video "{video_title}" (chunk {i+1}/{len(chunks)}, timestamps {chunk_start}s to {chunk_end}s).

Identify distinct learning segments. Each segment should represent a complete idea, lesson, or insight.

TRANSCRIPT:
{formatted_transcript}

Return a JSON object with this structure:
{{
  "segments": [
    {{
      "start_time": <start in seconds>,
      "end_time": <end in seconds>,
      "topic": "<main topic of this segment>",
      "context": "<brief description of what is discussed>"
    }}
  ]
}}

Only return valid JSON, no other text."""

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SEGMENTATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
                for seg in result.get('segments', []):
                    # Validate segment
                    duration = seg['end_time'] - seg['start_time']
                    if duration >= settings.min_segment_duration_seconds and \
                       duration <= settings.max_segment_duration_seconds:
                        all_segments.append(SegmentInfo(**seg))
                
            except Exception as e:
                logger.error("Segment identification failed for chunk", 
                           chunk_index=i, error=str(e))
                continue
        
        logger.info("Segment identification completed", segment_count=len(all_segments))
        return all_segments
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def extract_insights(
        self,
        segment_transcript: str,
        segment_topic: str,
        video_title: str
    ) -> InsightResult:
        """
        Generate title, summary, and takeaways for a segment
        """
        prompt = f"""Analyze this video segment and generate engaging content.

VIDEO: {video_title}
SEGMENT TOPIC: {segment_topic}

TRANSCRIPT:
{segment_transcript}

Generate:
1. A viral-worthy but professional title (max 60 chars)
2. A compelling 2-3 sentence summary
3. Exactly 3 key takeaways (actionable bullet points)
4. A relevance score 1-10 (how actionable is this advice?)
5. 1-3 categories from: [Leadership, Communication, Sales, Marketing, Productivity, Career Growth, Negotiation, Management, Entrepreneurship, Personal Finance, Networking, Innovation, Strategy, Mindset]

Return JSON:
{{
  "generated_title": "...",
  "summary_text": "...",
  "key_takeaways": ["...", "...", "..."],
  "relevance_score": 8,
  "categories": ["...", "..."]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return InsightResult(**result)
            
        except Exception as e:
            logger.error("Insight extraction failed", error=str(e))
            # Return default values
            return InsightResult(
                generated_title=segment_topic[:60],
                summary_text=segment_transcript[:200],
                key_takeaways=["Key insight from this segment"],
                relevance_score=5,
                categories=["Business"]
            )
    
    def get_segment_transcript(
        self,
        transcript_segments: List[dict],
        start_time: int,
        end_time: int
    ) -> str:
        """Extract transcript text for a specific time range"""
        texts = []
        for seg in transcript_segments:
            seg_start = seg['start']
            seg_end = seg['end']
            
            # Check for overlap
            if seg_end > start_time and seg_start < end_time:
                texts.append(seg['text'].strip())
        
        return " ".join(texts)
