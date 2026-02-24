"""
Phase 3: Blog/RSS Collector
============================
Monitors SEO industry blogs and RSS feeds for rule updates.

Created: 2025-12-28
Location: /opt/guru-intelligence/src/collectors/blog_rss_collector.py

Features:
- Monitors top SEO blogs via RSS
- Extracts article content
- Analyzes for actionable insights
- Deduplicates across sources
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BlogRSSCollector:
    """
    Collects expert insights from SEO industry blogs.
    
    Monitored sources:
    - Search Engine Journal
    - Search Engine Land
    - Moz Blog
    - Ahrefs Blog
    - Backlinko Blog
    """
    
    # RSS feeds to monitor
    RSS_FEEDS = {
        'search_engine_journal': {
            'url': 'https://www.searchenginejournal.com/feed/',
            'name': 'Search Engine Journal',
            'credibility_score': 0.90,
            'expertise_level': 'high'
        },
        'search_engine_land': {
            'url': 'https://searchengineland.com/feed',
            'name': 'Search Engine Land',
            'credibility_score': 0.92,
            'expertise_level': 'high'
        },
        'moz_blog': {
            'url': 'https://moz.com/blog/feed',
            'name': 'Moz Blog',
            'credibility_score': 0.93,
            'expertise_level': 'high'
        },
        'ahrefs_blog': {
            'url': 'https://ahrefs.com/blog/feed/',
            'name': 'Ahrefs Blog',
            'credibility_score': 0.94,
            'expertise_level': 'high'
        },
        'backlinko_blog': {
            'url': 'https://backlinko.com/blog/feed/',
            'name': 'Backlinko',
            'credibility_score': 0.91,
            'expertise_level': 'high'
        },
        'semrush_blog': {
            'url': 'https://www.semrush.com/blog/feed/',
            'name': 'SEMrush Blog',
            'credibility_score': 0.88,
            'expertise_level': 'medium'
        }
    }
    
    def __init__(self):
        """Initialize blog/RSS collector"""
        self.session = None
        logger.info(f"BlogRSSCollector initialized (monitoring {len(self.RSS_FEEDS)} feeds)")
    
    async def collect_recent_articles(
        self,
        days_back: int = 7,
        max_articles_per_feed: int = 10
    ) -> List[Dict]:
        """
        Collect recent articles from RSS feeds.
        
        Args:
            days_back: How many days back to look
            max_articles_per_feed: Max articles per feed
            
        Returns:
            List of article metadata dicts
        """
        logger.info(f"📰 Collecting RSS feed articles from last {days_back} days")
        
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        self.session = aiohttp.ClientSession()
        
        try:
            for feed_key, feed_info in self.RSS_FEEDS.items():
                try:
                    feed_articles = await self._parse_rss_feed(
                        feed_info,
                        cutoff_date,
                        max_articles_per_feed
                    )
                    articles.extend(feed_articles)
                    
                    logger.info(f"✅ {feed_info['name']}: {len(feed_articles)} articles")
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error collecting from {feed_info['name']}: {e}")
                    continue
            
        finally:
            await self.session.close()
        
        logger.info(f"✅ Collected {len(articles)} articles from RSS feeds")
        return articles
    
    async def _parse_rss_feed(
        self,
        feed_info: Dict,
        cutoff_date: datetime,
        max_articles: int
    ) -> List[Dict]:
        """Parse a single RSS feed"""
        try:
            # Fetch RSS feed
            async with self.session.get(feed_info['url'], timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {feed_info['name']}: HTTP {response.status}")
                    return []
                
                content = await response.text()
            
            # Parse RSS
            feed = feedparser.parse(content)
            
            articles = []
            for entry in feed.entries[:max_articles]:
                # Parse published date
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()
                
                # Skip old articles
                if pub_date < cutoff_date:
                    continue
                
                # Extract article data
                article = {
                    'title': entry.get('title', 'No title'),
                    'url': entry.get('link', ''),
                    'published_at': pub_date.isoformat(),
                    'summary': entry.get('summary', ''),
                    'author': entry.get('author', 'Unknown'),
                    'source': feed_info['name'],
                    'source_key': feed_key,
                    'credibility_score': feed_info['credibility_score']
                }
                
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_info['name']}: {e}")
            return []
    
    async def extract_article_content(self, url: str) -> Optional[str]:
        """
        Extract full article content from URL.
        
        Args:
            url: Article URL
            
        Returns:
            Full article text or None
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Extract main content (try common article containers)
            content = None
            for selector in ['article', 'main', '.post-content', '.entry-content', '.article-content']:
                content_tag = soup.select_one(selector)
                if content_tag:
                    content = content_tag.get_text(separator=' ', strip=True)
                    break
            
            # Fallback: get body text
            if not content:
                content = soup.get_text(separator=' ', strip=True)
            
            # Clean up
            content = self._clean_article_text(content)
            
            return content
            
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return None
    
    def _clean_article_text(self, text: str) -> str:
        """Clean and normalize article text"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common footer/header text
        noise_patterns = [
            r'Subscribe to.*?newsletter',
            r'Share this.*?Twitter',
            r'Click here to.*',
            r'Follow us on.*',
            r'Comments.*?Reply'
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    async def analyze_article_for_rules(
        self,
        article: Dict,
        content: str,
        rule_extractor = None
    ) -> List[Dict]:
        """
        Analyze article content to extract actionable rules.
        
        Args:
            article: Article metadata
            content: Full article text
            rule_extractor: Claude analyzer (optional)
            
        Returns:
            List of rule candidates
        """
        if not content or len(content) < 200:
            return []
        
        # Base confidence from source credibility
        base_confidence = article['credibility_score']
        
        # Detect data-backed claims
        has_data = any(keyword in content.lower() for keyword in [
            'study shows', 'research finds', 'data indicates', 'analysis reveals',
            'according to google', 'test results', 'case study'
        ])
        
        # Detect algorithm updates
        is_algorithm_update = any(keyword in content.lower() for keyword in [
            'google algorithm', 'core update', 'algorithm change', 'ranking update',
            'search algorithm', 'google confirmed'
        ])
        
        # Adjust confidence
        confidence = base_confidence
        if has_data:
            confidence += 0.05
        if is_algorithm_update:
            confidence += 0.10
        confidence = min(confidence, 0.95)
        
        # Extract key topics
        topics = self._extract_article_topics(content, article['title'])
        
        rule_candidates = []
        
        for topic in topics[:2]:  # Max 2 rules per article
            rule = {
                'rule_name': f"{article['source']}: {topic['title']}",
                'category': topic['category'],
                'tier': 1 if is_algorithm_update else 2,
                'definition': topic['summary'],
                'source_type': 'blog',
                'source_url': article['url'],
                'source_expert': article['author'],
                'confidence_score': confidence,
                'impact_estimate': 'high' if is_algorithm_update else topic['impact'],
                'evidence_strength': 'strong' if has_data else 'moderate',
                'supporting_data': {
                    'article_title': article['title'],
                    'source': article['source'],
                    'author': article['author'],
                    'published_at': article['published_at'],
                    'content_length': len(content),
                    'has_data_backing': has_data,
                    'is_algorithm_update': is_algorithm_update
                }
            }
            rule_candidates.append(rule)
        
        return rule_candidates
    
    def _extract_article_topics(self, content: str, title: str) -> List[Dict]:
        """Extract key topics from article content"""
        topics = []
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Topic detection patterns
        patterns = {
            'algorithm_update': {
                'keywords': ['algorithm update', 'core update', 'ranking change'],
                'category': 'Algorithm Updates',
                'impact': 'high'
            },
            'content_quality': {
                'keywords': ['content quality', 'e-e-a-t', 'helpful content', 'content guidelines'],
                'category': 'Content Strategy',
                'impact': 'high'
            },
            'technical_seo': {
                'keywords': ['core web vitals', 'page experience', 'site speed', 'crawling'],
                'category': 'Technical SEO',
                'impact': 'high'
            },
            'link_building': {
                'keywords': ['backlinks', 'link building', 'link quality', 'toxic links'],
                'category': 'Link Building',
                'impact': 'medium'
            },
            'local_seo': {
                'keywords': ['google business profile', 'local search', 'local rankings'],
                'category': 'Local SEO',
                'impact': 'medium'
            },
            'ai_search': {
                'keywords': ['ai overview', 'search generative', 'chatgpt', 'ai search'],
                'category': 'AI & Search',
                'impact': 'high'
            }
        }
        
        for topic_key, topic_info in patterns.items():
            # Check title and content
            title_match = any(kw in title_lower for kw in topic_info['keywords'])
            content_matches = [kw for kw in topic_info['keywords'] if kw in content_lower]
            
            if title_match or content_matches:
                # Extract context
                if content_matches:
                    first_match = content_matches[0]
                    match_pos = content_lower.find(first_match)
                    start = max(0, match_pos - 150)
                    end = min(len(content), match_pos + 250)
                    context = content[start:end].strip()
                else:
                    # Use first 400 chars if title matches
                    context = content[:400].strip()
                
                topics.append({
                    'title': topic_info['keywords'][0].title(),
                    'category': topic_info['category'],
                    'impact': topic_info['impact'],
                    'summary': context,
                    'matched_in_title': title_match,
                    'matched_keywords': content_matches
                })
        
        return topics
    
    async def run_collection_cycle(
        self,
        days_back: int = 7,
        max_articles_per_feed: int = 10
    ) -> Tuple[int, int]:
        """
        Run a complete blog/RSS collection cycle.
        
        Returns:
            (articles_analyzed, rules_extracted): Counts
        """
        logger.info("🚀 Starting blog/RSS collection cycle")
        
        # Collect recent articles
        articles = await self.collect_recent_articles(days_back, max_articles_per_feed)
        
        rules_extracted = 0
        articles_analyzed = 0
        
        for article in articles:
            try:
                # Extract full content
                content = await self.extract_article_content(article['url'])
                
                if content:
                    # Analyze for rules
                    rules = await self.analyze_article_for_rules(article, content)
                    rules_extracted += len(rules)
                    articles_analyzed += 1
                    
                    if rules:
                        logger.info(f"✅ Analyzed '{article['title'][:50]}...' - extracted {len(rules)} rules")
                
                # Rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error analyzing article {article['url']}: {e}")
                continue
        
        logger.info(f"✅ Blog/RSS cycle complete: {articles_analyzed} articles analyzed, {rules_extracted} rules extracted")
        return articles_analyzed, rules_extracted


# Standalone testing
if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_collector():
        collector = BlogRSSCollector()
        
        # Collect recent articles
        articles = await collector.collect_recent_articles(days_back=3, max_articles_per_feed=3)
        
        print(f"\n📰 Collected {len(articles)} articles:\n")
        for article in articles[:5]:
            print(f"  • [{article['source']}] {article['title']}")
            print(f"    URL: {article['url']}")
            print(f"    Author: {article['author']}")
            print(f"    Published: {article['published_at']}")
            print()
    
    asyncio.run(test_collector())
