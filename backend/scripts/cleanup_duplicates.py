#!/usr/bin/env python3
"""
Script to clean up duplicate videos/segments and organize the database.

Usage:
    python scripts/cleanup_duplicates.py --check       # Dry run - only show duplicates
    python scripts/cleanup_duplicates.py --clean       # Actually remove duplicates
    python scripts/cleanup_duplicates.py --clean-all   # Clean duplicates + orphans + sync embeddings
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import datetime
from collections import defaultdict
from sqlalchemy import func, text
import structlog

from app.db.session import get_db_session
from app.db.models.video import Video, VideoStatus
from app.db.models.segment import Segment
from app.db.models.channel import Channel
from app.db.models.category import SegmentCategory
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger()


class DatabaseCleaner:
    def __init__(self, dry_run: bool = True):
        self.db = get_db_session()
        self.dry_run = dry_run
        self.stats = {
            "duplicate_videos": 0,
            "duplicate_segments": 0,
            "orphan_segments": 0,
            "orphan_embeddings": 0,
            "failed_videos_cleaned": 0,
        }
    
    def find_duplicate_videos(self):
        """Find videos with duplicate youtube_id"""
        print("\n" + "="*60)
        print("🔍 Checking for duplicate videos...")
        print("="*60)
        
        # Group by youtube_id
        duplicates = self.db.query(
            Video.youtube_id,
            func.count(Video.id).label('count'),
            func.array_agg(Video.id).label('ids')
        ).group_by(Video.youtube_id).having(func.count(Video.id) > 1).all()
        
        if not duplicates:
            print("✅ No duplicate videos found")
            return []
        
        print(f"⚠️  Found {len(duplicates)} youtube_ids with duplicates:\n")
        
        dup_list = []
        for dup in duplicates:
            print(f"  YouTube ID: {dup.youtube_id} ({dup.count} copies)")
            
            # Get details of each duplicate
            videos = self.db.query(Video).filter(
                Video.youtube_id == dup.youtube_id
            ).order_by(Video.created_at).all()
            
            for v in videos:
                seg_count = len(v.segments) if v.segments else 0
                print(f"    - ID: {v.id[:8]}... | Status: {v.status:12} | "
                      f"Segments: {seg_count:3} | Created: {v.created_at}")
            
            dup_list.append({
                "youtube_id": dup.youtube_id,
                "videos": videos
            })
        
        return dup_list
    
    def clean_duplicate_videos(self, duplicates: list):
        """Remove duplicate videos, keeping the best one"""
        print("\n🧹 Cleaning duplicate videos...")
        
        for dup in duplicates:
            videos = dup["videos"]
            
            # Strategy: Keep the one with most segments and INDEXED status
            # Priority: INDEXED > other status, then most segments, then newest
            
            def score_video(v):
                seg_count = len(v.segments) if v.segments else 0
                is_indexed = 1 if v.status == VideoStatus.INDEXED.value else 0
                return (is_indexed, seg_count, v.created_at)
            
            videos_sorted = sorted(videos, key=score_video, reverse=True)
            keep = videos_sorted[0]
            to_delete = videos_sorted[1:]
            
            print(f"\n  {dup['youtube_id']}:")
            print(f"    ✅ Keeping: {keep.id[:8]}... ({keep.status}, {len(keep.segments) if keep.segments else 0} segments)")
            
            for v in to_delete:
                print(f"    ❌ Removing: {v.id[:8]}... ({v.status}, {len(v.segments) if v.segments else 0} segments)")
                
                if not self.dry_run:
                    # Delete embeddings first
                    try:
                        embedding_service = EmbeddingService()
                        embedding_service.delete_video_embeddings(str(v.id))
                    except Exception as e:
                        print(f"       Warning: Failed to delete embeddings: {e}")
                    
                    # Delete video (cascade deletes segments)
                    self.db.delete(v)
                    self.stats["duplicate_videos"] += 1
        
        if not self.dry_run:
            self.db.commit()
            print(f"\n✅ Removed {self.stats['duplicate_videos']} duplicate videos")
    
    def find_duplicate_segments(self):
        """Find segments with same video_id and overlapping times"""
        print("\n" + "="*60)
        print("🔍 Checking for duplicate segments...")
        print("="*60)
        
        # Find exact duplicates (same video, start, end)
        duplicates = self.db.query(
            Segment.video_id,
            Segment.start_time,
            Segment.end_time,
            func.count(Segment.id).label('count'),
            func.array_agg(Segment.id).label('ids')
        ).group_by(
            Segment.video_id, 
            Segment.start_time, 
            Segment.end_time
        ).having(func.count(Segment.id) > 1).all()
        
        if not duplicates:
            print("✅ No duplicate segments found")
            return []
        
        print(f"⚠️  Found {len(duplicates)} segment duplicates:\n")
        
        for dup in duplicates[:10]:  # Show first 10
            print(f"  Video: {dup.video_id[:8]}... | "
                  f"Time: {dup.start_time:.1f}s - {dup.end_time:.1f}s | "
                  f"Count: {dup.count}")
        
        if len(duplicates) > 10:
            print(f"  ... and {len(duplicates) - 10} more")
        
        return duplicates
    
    def clean_duplicate_segments(self, duplicates: list):
        """Remove duplicate segments, keeping one"""
        print("\n🧹 Cleaning duplicate segments...")
        
        for dup in duplicates:
            segments = self.db.query(Segment).filter(
                Segment.video_id == dup.video_id,
                Segment.start_time == dup.start_time,
                Segment.end_time == dup.end_time
            ).order_by(Segment.created_at).all()
            
            # Keep the first one (oldest)
            keep = segments[0]
            to_delete = segments[1:]
            
            for seg in to_delete:
                if not self.dry_run:
                    # Delete embedding
                    if seg.embedding_id:
                        try:
                            embedding_service = EmbeddingService()
                            embedding_service.delete_segment_embedding(seg.embedding_id)
                        except:
                            pass
                    
                    self.db.delete(seg)
                    self.stats["duplicate_segments"] += 1
        
        if not self.dry_run:
            self.db.commit()
            print(f"✅ Removed {self.stats['duplicate_segments']} duplicate segments")
    
    def find_orphan_segments(self):
        """Find segments without valid video reference"""
        print("\n" + "="*60)
        print("🔍 Checking for orphan segments...")
        print("="*60)
        
        # Segments with video that doesn't exist
        orphans = self.db.query(Segment).outerjoin(Video).filter(
            Video.id == None
        ).all()
        
        if not orphans:
            print("✅ No orphan segments found")
            return []
        
        print(f"⚠️  Found {len(orphans)} orphan segments")
        return orphans
    
    def clean_orphan_segments(self, orphans: list):
        """Remove segments without valid video"""
        print("\n🧹 Cleaning orphan segments...")
        
        for seg in orphans:
            if not self.dry_run:
                if seg.embedding_id:
                    try:
                        embedding_service = EmbeddingService()
                        embedding_service.delete_segment_embedding(seg.embedding_id)
                    except:
                        pass
                
                self.db.delete(seg)
                self.stats["orphan_segments"] += 1
        
        if not self.dry_run:
            self.db.commit()
            print(f"✅ Removed {self.stats['orphan_segments']} orphan segments")
    
    def check_embedding_sync(self):
        """Check if Qdrant embeddings are in sync with database"""
        print("\n" + "="*60)
        print("🔍 Checking embedding synchronization...")
        print("="*60)
        
        try:
            embedding_service = EmbeddingService()
            stats = embedding_service.get_collection_stats()
            
            db_segments = self.db.query(Segment).filter(
                Segment.embedding_id != None
            ).count()
            
            indexed_videos = self.db.query(Video).filter(
                Video.status == VideoStatus.INDEXED.value
            ).count()
            
            print(f"  📊 Qdrant vectors: {stats.get('vectors_count', 'N/A')}")
            print(f"  📊 DB segments with embeddings: {db_segments}")
            print(f"  📊 Indexed videos: {indexed_videos}")
            
            return stats
        except Exception as e:
            print(f"  ❌ Could not connect to Qdrant: {e}")
            return None
    
    def show_summary(self):
        """Show database summary and organization stats"""
        print("\n" + "="*60)
        print("📊 DATABASE SUMMARY")
        print("="*60)
        
        # Video stats by status
        status_counts = self.db.query(
            Video.status,
            func.count(Video.id)
        ).group_by(Video.status).all()
        
        print("\n📹 Videos by status:")
        for status, count in status_counts:
            print(f"    {status:15}: {count}")
        
        # Channel stats
        channel_stats = self.db.query(
            Channel.name,
            func.count(Video.id).label('video_count')
        ).outerjoin(Video).group_by(Channel.id).order_by(
            func.count(Video.id).desc()
        ).limit(10).all()
        
        print("\n📺 Top channels by video count:")
        for name, count in channel_stats:
            print(f"    {name[:30]:30}: {count} videos")
        
        # Segment stats
        total_segments = self.db.query(func.count(Segment.id)).scalar()
        segments_with_embedding = self.db.query(func.count(Segment.id)).filter(
            Segment.embedding_id != None
        ).scalar()
        
        print(f"\n🎬 Segments:")
        print(f"    Total: {total_segments}")
        print(f"    With embeddings: {segments_with_embedding}")
        
        # Average segments per video
        avg_segments = self.db.query(
            func.avg(
                self.db.query(func.count(Segment.id))
                .filter(Segment.video_id == Video.id)
                .correlate(Video)
                .scalar_subquery()
            )
        ).filter(Video.status == VideoStatus.INDEXED.value).scalar()
        
        if avg_segments:
            print(f"    Avg per indexed video: {avg_segments:.1f}")
    
    def clean_failed_videos(self, days_old: int = 7):
        """Clean up old failed videos"""
        print("\n" + "="*60)
        print(f"🔍 Checking for failed videos older than {days_old} days...")
        print("="*60)
        
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        failed = self.db.query(Video).filter(
            Video.status == VideoStatus.FAILED.value,
            Video.updated_at < cutoff
        ).all()
        
        if not failed:
            print("✅ No old failed videos to clean")
            return
        
        print(f"⚠️  Found {len(failed)} old failed videos")
        
        for v in failed:
            print(f"    {v.youtube_id}: {v.processing_error[:50] if v.processing_error else 'No error message'}...")
            
            if not self.dry_run:
                self.db.delete(v)
                self.stats["failed_videos_cleaned"] += 1
        
        if not self.dry_run:
            self.db.commit()
            print(f"✅ Removed {self.stats['failed_videos_cleaned']} old failed videos")
    
    def run_full_cleanup(self):
        """Run all cleanup operations"""
        # Show current state
        self.show_summary()
        
        # Find and clean duplicates
        dup_videos = self.find_duplicate_videos()
        if dup_videos:
            self.clean_duplicate_videos(dup_videos)
        
        dup_segments = self.find_duplicate_segments()
        if dup_segments:
            self.clean_duplicate_segments(dup_segments)
        
        # Find and clean orphans
        orphan_segments = self.find_orphan_segments()
        if orphan_segments:
            self.clean_orphan_segments(orphan_segments)
        
        # Clean failed videos
        self.clean_failed_videos()
        
        # Check embedding sync
        self.check_embedding_sync()
        
        # Final summary
        print("\n" + "="*60)
        print("📋 CLEANUP SUMMARY")
        print("="*60)
        
        if self.dry_run:
            print("🔸 DRY RUN - No changes were made")
        else:
            print("✅ Changes applied:")
        
        print(f"    Duplicate videos removed: {self.stats['duplicate_videos']}")
        print(f"    Duplicate segments removed: {self.stats['duplicate_segments']}")
        print(f"    Orphan segments removed: {self.stats['orphan_segments']}")
        print(f"    Failed videos cleaned: {self.stats['failed_videos_cleaned']}")
    
    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Clean up duplicate videos and organize the database"
    )
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Dry run - only show duplicates without removing"
    )
    parser.add_argument(
        "--clean",
        action="store_true", 
        help="Remove duplicates and organize"
    )
    parser.add_argument(
        "--clean-all",
        action="store_true",
        help="Full cleanup including orphans and failed videos"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Just show database summary"
    )
    
    args = parser.parse_args()
    
    if not any([args.check, args.clean, args.clean_all, args.summary]):
        parser.print_help()
        return
    
    dry_run = not (args.clean or args.clean_all)
    
    print("\n" + "="*60)
    print("🛠️  BizSkill Database Cleanup Tool")
    print("="*60)
    
    if dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    else:
        print("Mode: LIVE (changes will be applied)")
    
    cleaner = DatabaseCleaner(dry_run=dry_run)
    
    try:
        if args.summary:
            cleaner.show_summary()
        else:
            cleaner.run_full_cleanup()
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
