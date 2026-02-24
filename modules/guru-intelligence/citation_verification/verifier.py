
"""
Citation Verification Module for RevSEO Intelligence™
Verifies AI citations are real and accurate (not hallucinated)
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)


class CitationVerifier:
    """
    Verifies citations from AI platforms are:
    1. Real URLs that resolve
    2. Contain relevant content
    3. Match anchor text claims
    """
    
    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; RevFlowBot/1.0; +https://revflow.ai)'}
        )
        
    async def verify_citation(self, citation: Dict, query_context: str) -> Dict:
        """Verify a single citation"""
        result = {
            'url': citation.get('url'),
            'verified': False,
            'score': 0,
            'issues': [],
            'checks': {}
        }
        
        url = citation.get('url')
        if not url:
            result['issues'].append('Missing URL')
            return result
        
        # Check 1: URL resolves
        try:
            response = await self.client.get(url)
            result['checks']['url_resolves'] = response.status_code == 200
            result['checks']['status_code'] = response.status_code
            
            if response.status_code != 200:
                result['issues'].append(f'HTTP {response.status_code}')
                return result
                
        except httpx.TimeoutException:
            result['issues'].append('Timeout')
            result['checks']['url_resolves'] = False
            return result
        except Exception as e:
            result['issues'].append(f'Error: {str(e)[:50]}')
            result['checks']['url_resolves'] = False
            return result
        
        # Check 2: Content relevance
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(['script', 'style', 'nav', 'footer']):
                script.decompose()
            page_text = soup.get_text(separator=' ', strip=True).lower()
            
            query_terms = self._extract_key_terms(query_context)
            
            matches = sum(1 for term in query_terms if term.lower() in page_text)
            relevance_score = matches / len(query_terms) if query_terms else 0
            
            result['checks']['content_relevant'] = relevance_score > 0.3
            result['checks']['relevance_score'] = round(relevance_score, 2)
            
            if relevance_score < 0.3:
                result['issues'].append('Low relevance')
                
        except Exception as e:
            result['issues'].append(f'Parse error: {str(e)[:30]}')
            result['checks']['content_relevant'] = False
        
        # Check 3: Anchor text presence
        anchor_text = citation.get('anchor_text', '')
        if anchor_text and len(anchor_text) > 3:
            anchor_in_page = anchor_text.lower() in page_text
            result['checks']['anchor_found'] = anchor_in_page
            if not anchor_in_page:
                result['issues'].append('Anchor not found')
        
        # Calculate score
        score = 0
        if result['checks'].get('url_resolves'):
            score += 40
        if result['checks'].get('content_relevant'):
            score += 40
        if result['checks'].get('anchor_found', True):
            score += 20
            
        result['score'] = score
        result['verified'] = score >= 60
        
        return result
    
    async def verify_batch(self, citations: List[Dict], query_context: str,
                          max_concurrent: int = 5) -> Dict:
        """Verify multiple citations with concurrency limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_limit(citation):
            async with semaphore:
                return await self.verify_citation(citation, query_context)
        
        tasks = [verify_with_limit(c) for c in citations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        verified_count = 0
        total_score = 0
        verification_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                verification_results.append({
                    'url': citations[i].get('url'),
                    'verified': False,
                    'error': str(result)[:100]
                })
            else:
                verification_results.append(result)
                if result.get('verified'):
                    verified_count += 1
                total_score += result.get('score', 0)
        
        return {
            'total_citations': len(citations),
            'verified_count': verified_count,
            'verification_rate': round(verified_count / len(citations) * 100, 1) if citations else 0,
            'average_score': round(total_score / len(citations), 1) if citations else 0,
            'results': verification_results
        }
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms for relevance checking"""
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'who',
            'where', 'when', 'why', 'how', 'i', 'me', 'my', 'we', 'our',
            'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but',
            'best', 'top', 'good', 'need', 'want', 'looking', 'find'
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        return [w for w in words if w not in stopwords][:10]
    
    async def close(self):
        await self.client.aclose()
