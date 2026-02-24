"""
RevCite: Microsoft Clarity Citation Engagement Tracker
Tracks which AI citations users actually engage with
"""

import json
from typing import Dict, List
from datetime import datetime


class CitationEngagementTracker:
    """Track citation engagement using Microsoft Clarity"""
    
    def __init__(self, clarity_project_id: str):
        self.project_id = clarity_project_id
        
    def get_enhanced_tracking_code(self, page_url: str, citations: List[Dict]) -> str:
        """Generate Clarity tracking with citation event tracking"""
        
        tracking_code = f'''
<!-- RevCite: Clarity Citation Tracking -->
<script type="text/javascript">
    (function(c,l,a,r,i,t,y){{
        c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    }})(window, document, "clarity", "script", "{self.project_id}");
    
    // Citation click tracking
    window.addEventListener('load', function() {{
        document.querySelectorAll('a[data-citation-id]').forEach(function(link) {{
            link.addEventListener('click', function(e) {{
                if (typeof clarity === 'function') {{
                    clarity('event', 'citation_click', {{
                        citation_id: this.getAttribute('data-citation-id'),
                        source: this.getAttribute('data-citation-source'),
                        ai_engine: this.getAttribute('data-ai-engine')
                    }});
                }}
            }});
        }});
    }});
</script>
'''
        return tracking_code
    
    def calculate_citation_authority_score(self, clarity_data: Dict) -> float:
        """Convert citation engagement to authority score (0-100)"""
        
        ctr = clarity_data.get("avg_citation_ctr", 0)
        dwell_time = clarity_data.get("avg_dwell_time_seconds", 0)
        visibility_rate = clarity_data.get("visibility_rate", 0)
        
        score = (
            (ctr * 100) * 0.40 +
            min(dwell_time / 180, 1) * 35 +
            (visibility_rate * 100) * 0.25
        )
        
        return min(100, max(0, score))


if __name__ == "__main__":
    # Test
    tracker = CitationEngagementTracker("test-project-id")
    print("✅ Clarity tracker initialized")
