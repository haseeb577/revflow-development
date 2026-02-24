"""
Phase 3: YouTube Collector
===========================
Collects and analyzes content from expert SEO YouTube channels.
Extracts actionable rules from video transcripts.

Created: 2025-12-28
Location: /opt/guru-intelligence/src/collectors/youtube_collector.py

Features:
- Monitors top SEO/marketing channels
- Downloads video transcripts
- Analyzes for actionable insights
- Submits to approval workflow
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class YouTubeCollector:
    """
    Collects expert insights from YouTube SEO channels.
    
    Monitored channels:
    - Ahrefs
    - Moz
    - Backlinko
    - Neil Patel
    - SEMrush
    - Search Engine Journal
    """
    
    # YouTube channels to monitor (channel IDs)
    EXPERT_CHANNELS = {
        'ahrefs': {
            'channel_id': 'UCWquNQV8Y0_defMKnGKrFOQ',
            'name': 'Ahrefs',
            'expertise_level': 'high',
            'credibility_score': 0.95
        },
        'moz': {
            'channel_id': 'UCs26XZBwrSZLiTEH8wEi0fg',
            'name': 'Moz',
            'expertise_level': 'high',
            'credibility_score': 0.93
        },
        'backlinko': {
            'channel_id': 'UCx7J37QuXsGL7QG6SMIpqKg',
            'name': 'Backlinko',
            'expertise_level': 'high',
            'credibility_score': 0.92
        },
        'neilpatel': {
            'channel_id': 'UCl-Zrl0QhF66lu1aGXaTbfw',
            'name': 'Neil Patel',
            'expertise_level': 'medium',
            'credibility_score': 0.85
        },
        'semrush': {
            'channel_id': 'UCvZkRfq7q79r7irxo6xXRYg',
            'name': 'SEMrush',
            'expertise_level': 'high',
            'credibility_score': 0.90
        }
    }
    
    def __init__(self, youtube_api_key: Optional[str] = None):
        """
        Initialize YouTube collector.
        
        Args:
            youtube_api_key: Google YouTube Data API key (optional, enhances capabilities)
        """
        self.api_key = youtube_api_key
        self.youtube = None
        
        if youtube_api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
                logger.info("✅ YouTube API client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize YouTube API: {e}")
        
        logger.info(f"YouTubeCollector initialized (monitoring {len(self.EXPERT_CHANNELS)} channels)")
    
    async def collect_recent_videos(
        self,
        days_back: int = 7,
        max_videos_per_channel: int = 5
    ) -> List[Dict]:
        """
        Collect recent videos from expert channels.
        
        Args:
            days_back: How many days back to look
            max_videos_per_channel: Max videos to process per channel
            
        Returns:
            List of video metadata dicts
        """
        logger.info(f"🎥 Collecting YouTube videos from last {days_back} days")
        
        videos = []
        
        for channel_key, channel_info in self.EXPERT_CHANNELS.items():
            try:
                channel_videos = await self._get_channel_videos(
                    channel_info,
                    days_back,
                    max_videos_per_channel
                )
                videos.extend(channel_videos)
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error collecting from {channel_info['name']}: {e}")
                continue
        
        logger.info(f"✅ Collected {len(videos)} videos from YouTube")
        return videos
    
    async def _get_channel_videos(
        self,
        channel_info: Dict,
        days_back: int,
        max_videos: int
    ) -> List[Dict]:
        """Get recent videos from a specific channel"""
        videos = []
        
        if self.youtube:
            # Use YouTube API for better results
            videos = await self._get_videos_via_api(channel_info, days_back, max_videos)
        else:
            # Fallback: use RSS feed (less reliable but no API key needed)
            videos = await self._get_videos_via_rss(channel_info, max_videos)
        
        return videos
    
    async def _get_videos_via_api(
        self,
        channel_info: Dict,
        days_back: int,
        max_videos: int
    ) -> List[Dict]:
        """Get videos using YouTube Data API"""
        try:
            # Calculate date threshold
            published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            
            # Search for recent videos
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_info['channel_id'],
                type='video',
                order='date',
                publishedAfter=published_after,
                maxResults=max_videos
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                videos.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'published_at': snippet['publishedAt'],
                    'channel': channel_info['name'],
                    'channel_key': channel_info.get('name', '').lower().replace(' ', ''),
                    'url': f'https://youtube.com/watch?v={video_id}',
                    'credibility_score': channel_info['credibility_score']
                })
            
            return videos
            
        except Exception as e:
            logger.error(f"YouTube API error for {channel_info['name']}: {e}")
            return []
    
    async def _get_videos_via_rss(
        self,
        channel_info: Dict,
        max_videos: int
    ) -> List[Dict]:
        """Fallback: Get videos via RSS feed (no API key required)"""
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_info['channel_id']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url) as response:
                    if response.status != 200:
                        return []
                    
                    xml_content = await response.text()
                    
                    # Parse XML (simple regex extraction)
                    videos = []
                    video_pattern = r'<entry>.*?<yt:videoId>(.*?)</yt:videoId>.*?<title>(.*?)</title>.*?<published>(.*?)</published>.*?</entry>'
                    matches = re.findall(video_pattern, xml_content, re.DOTALL)
                    
                    for video_id, title, published in matches[:max_videos]:
                        # Decode HTML entities
                        title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                        
                        videos.append({
                            'video_id': video_id,
                            'title': title,
                            'description': '',
                            'published_at': published,
                            'channel': channel_info['name'],
                            'channel_key': channel_info.get('name', '').lower().replace(' ', ''),
                            'url': f'https://youtube.com/watch?v={video_id}',
                            'credibility_score': channel_info['credibility_score']
                        })
                    
                    return videos
                    
        except Exception as e:
            logger.error(f"RSS feed error for {channel_info['name']}: {e}")
            return []
    
    async def extract_transcript(self, video_id: str) -> Optional[str]:
        """
        Extract transcript from YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full transcript text or None if unavailable
        """
        try:
            # Get transcript (auto-generated or manual)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine all text segments
            full_text = ' '.join([entry['text'] for entry in transcript_list])
            
            # Clean up transcript
            full_text = self._clean_transcript(full_text)
            
            return full_text
            
        except Exception as e:
            logger.warning(f"No transcript available for video {video_id}: {e}")
            return None
    
    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text"""
        # Remove [Music], [Applause], etc.
        text = re.sub(r'\[.*?\]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove duplicate sentences (auto-captions often repeat)
        sentences = text.split('. ')
        unique_sentences = []
        seen = set()
        for sent in sentences:
            normalized = sent.lower().strip()
            if normalized and normalized not in seen:
                unique_sentences.append(sent)
                seen.add(normalized)
        
        return '. '.join(unique_sentences)
    
    async def analyze_video_for_rules(
        self,
        video: Dict,
        transcript: str,
        rule_extractor = None  # Will be Claude-based analyzer
    ) -> List[Dict]:
        """
        Analyze video transcript to extract actionable rules.
        
        Args:
            video: Video metadata dict
            transcript: Full transcript text
            rule_extractor: Claude AI analyzer (optional, pass from main service)
            
        Returns:
            List of rule candidates
        """
        if not transcript or len(transcript) < 100:
            return []
        
        # TODO: Integrate with Claude rule extractor
        # For now, return placeholder structure
        
        # Calculate base confidence from channel credibility
        base_confidence = video['credibility_score']
        
        # Detect if video discusses data/studies (increases confidence)
        has_data = any(keyword in transcript.lower() for keyword in [
            'study', 'research', 'data', 'found that', 'according to',
            'analysis', 'tested', 'experiment'
        ])
        
        confidence_adjustment = 0.05 if has_data else 0
        
        # Extract key topics
        topics = self._extract_key_topics(transcript)
        
        rule_candidates = []
        
        # Generate rule suggestions based on content
        # (In production, this would call Claude API)
        for topic in topics[:3]:  # Max 3 rules per video
            rule = {
                'rule_name': f"{video['channel']}: {topic['title']}",
                'category': topic['category'],
                'tier': 2,  # YouTube content typically tier 2
                'definition': topic['summary'],
                'source_type': 'youtube',
                'source_url': video['url'],
                'source_expert': video['channel'],
                'confidence_score': min(base_confidence + confidence_adjustment, 0.95),
                'impact_estimate': topic['impact'],
                'evidence_strength': 'strong' if has_data else 'moderate',
                'supporting_data': {
                    'video_title': video['title'],
                    'channel': video['channel'],
                    'published_at': video['published_at'],
                    'transcript_length': len(transcript),
                    'has_data_backing': has_data,
                    'extracted_topics': [t['title'] for t in topics]
                }
            }
            rule_candidates.append(rule)
        
        return rule_candidates
    
    def _extract_key_topics(self, transcript: str) -> List[Dict]:
        """
        Extract key topics from transcript using keyword matching.
        
        In production, this would use Claude for better extraction.
        """
        topics = []
        
        # SEO topic patterns
        patterns = {
            'content': {
                'keywords': ['content quality', 'e-e-a-t', 'helpful content', 'user intent'],
                'category': 'Content Strategy',
                'impact': 'high'
            },
            'technical': {
                'keywords': ['core web vitals', 'page speed', 'javascript', 'crawling'],
                'category': 'Technical SEO',
                'impact': 'high'
            },
            'links': {
                'keywords': ['backlinks', 'link building', 'anchor text', 'domain authority'],
                'category': 'Link Building',
                'impact': 'medium'
            },
            'local': {
                'keywords': ['google business profile', 'local seo', 'map pack'],
                'category': 'Local SEO',
                'impact': 'medium'
            }
        }
        
        transcript_lower = transcript.lower()
        
        for topic_key, topic_info in patterns.items():
            # Check if any keywords are present
            matches = [kw for kw in topic_info['keywords'] if kw in transcript_lower]
            
            if matches:
                # Extract context around first match
                first_match = matches[0]
                match_pos = transcript_lower.find(first_match)
                
                # Get ~200 chars of context
                start = max(0, match_pos - 100)
                end = min(len(transcript), match_pos + 200)
                context = transcript[start:end].strip()
                
                topics.append({
                    'title': topic_info['keywords'][0].title(),
                    'category': topic_info['category'],
                    'impact': topic_info['impact'],
                    'summary': context,
                    'matched_keywords': matches
                })
        
        return topics
    
    async def run_collection_cycle(
        self,
        days_back: int = 7,
        max_videos_per_channel: int = 5
    ) -> Tuple[int, int]:
        """
        Run a complete YouTube collection cycle.
        
        Returns:
            (videos_analyzed, rules_extracted): Counts
        """
        logger.info("🚀 Starting YouTube collection cycle")
        
        # Collect recent videos
        videos = await self.collect_recent_videos(days_back, max_videos_per_channel)
        
        rules_extracted = 0
        videos_analyzed = 0
        
        for video in videos:
            try:
                # Get transcript
                transcript = await self.extract_transcript(video['video_id'])
                
                if transcript:
                    # Analyze for rules
                    rules = await self.analyze_video_for_rules(video, transcript)
                    rules_extracted += len(rules)
                    videos_analyzed += 1
                    
                    logger.info(f"✅ Analyzed '{video['title']}' - extracted {len(rules)} rules")
                
                # Rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error analyzing video {video['video_id']}: {e}")
                continue
        
        logger.info(f"✅ YouTube cycle complete: {videos_analyzed} videos analyzed, {rules_extracted} rules extracted")
        return videos_analyzed, rules_extracted


# Standalone testing
if __name__ == "__main__":
    import asyncio
    import os
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_collector():
        # Get API key from environment (optional)
        api_key = os.getenv('YOUTUBE_API_KEY')
        
        collector = YouTubeCollector(youtube_api_key=api_key)
        
        # Collect recent videos
        videos = await collector.collect_recent_videos(days_back=7, max_videos_per_channel=2)
        
        print(f"\n📺 Collected {len(videos)} videos:\n")
        for video in videos[:5]:
            print(f"  • [{video['channel']}] {video['title']}")
            print(f"    URL: {video['url']}")
            print(f"    Published: {video['published_at']}")
            print()
    
    asyncio.run(test_collector())
