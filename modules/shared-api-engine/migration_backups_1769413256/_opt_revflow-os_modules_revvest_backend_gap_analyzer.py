"""
RevVest IQ - Micro-Site Gap Analyzer
Module 14 - Digital Landlord Suite
Identifies underserved niches and market opportunities
"""

import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REVSPY_URL = "http://localhost:8160"


@dataclass
class GapOpportunity:
    """Represents a market gap opportunity"""
    niche: str
    gap_type: str
    severity: int  # 1-10
    description: str
    keywords: List[str]
    estimated_potential: float
    action_items: List[str]


class GapAnalyzer:
    """Analyzes markets for content and service gaps"""

    def __init__(self):
        self.revspy_url = REVSPY_URL

    def analyze_niche_gaps(self, niche: str, zip_code: Optional[str] = None) -> List[GapOpportunity]:
        """
        Analyze a niche for micro-site opportunities

        Args:
            niche: Target niche/industry
            zip_code: Optional geographic filter

        Returns:
            List of gap opportunities
        """
        gaps = []

        # Get SERP blindspot data from RevSPY
        serp_gaps = self._get_serp_gaps(niche, zip_code)
        gaps.extend(serp_gaps)

        # Analyze content gaps
        content_gaps = self._analyze_content_gaps(niche)
        gaps.extend(content_gaps)

        # Analyze local service gaps
        if zip_code:
            local_gaps = self._analyze_local_gaps(niche, zip_code)
            gaps.extend(local_gaps)

        # Sort by severity
        gaps.sort(key=lambda x: x.severity, reverse=True)

        return gaps

    def _get_serp_gaps(self, niche: str, zip_code: Optional[str]) -> List[GapOpportunity]:
        """Fetch SERP gaps from RevSPY (Module 15)"""
        gaps = []

        try:
            params = {'niche': niche}
            if zip_code:
                params['zip_code'] = zip_code

            response = requests.get(
                f"{self.revspy_url}/api/blindspots",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                for blindspot in data.get('blindspots', []):
                    gap = GapOpportunity(
                        niche=niche,
                        gap_type='serp_blindspot',
                        severity=blindspot.get('severity', 5),
                        description=blindspot.get('description', f"SERP gap identified in {niche}"),
                        keywords=blindspot.get('keywords', []),
                        estimated_potential=blindspot.get('traffic_potential', 0),
                        action_items=[
                            f"Create content targeting: {', '.join(blindspot.get('keywords', [])[:3])}",
                            "Build topical authority around this gap",
                            "Monitor competitor response"
                        ]
                    )
                    gaps.append(gap)

        except requests.RequestException as e:
            logger.warning(f"Could not fetch RevSPY data: {e}")
            # Return estimated gaps without API data
            gaps.append(GapOpportunity(
                niche=niche,
                gap_type='estimated_serp_gap',
                severity=5,
                description=f"Potential SERP gaps in {niche} (RevSPY data unavailable)",
                keywords=[f"{niche} services", f"{niche} near me", f"best {niche}"],
                estimated_potential=1000,
                action_items=[
                    "Run full SERP analysis when RevSPY available",
                    "Research competitor rankings manually",
                    "Identify long-tail variations"
                ]
            ))

        return gaps

    def _analyze_content_gaps(self, niche: str) -> List[GapOpportunity]:
        """Analyze content gaps in a niche"""
        gaps = []

        # Common content gap patterns
        content_patterns = [
            {
                'type': 'comparison_content',
                'description': f"Missing comparison content for {niche}",
                'keywords': [f"{niche} vs", f"best {niche}", f"{niche} comparison"],
                'severity': 7
            },
            {
                'type': 'how_to_content',
                'description': f"Underserved how-to content for {niche}",
                'keywords': [f"how to {niche}", f"{niche} guide", f"{niche} tutorial"],
                'severity': 6
            },
            {
                'type': 'cost_content',
                'description': f"Missing pricing/cost content for {niche}",
                'keywords': [f"{niche} cost", f"{niche} price", f"how much {niche}"],
                'severity': 8
            },
            {
                'type': 'local_content',
                'description': f"Local {niche} content opportunity",
                'keywords': [f"{niche} near me", f"local {niche}", f"{niche} in [city]"],
                'severity': 7
            }
        ]

        for pattern in content_patterns:
            gap = GapOpportunity(
                niche=niche,
                gap_type=pattern['type'],
                severity=pattern['severity'],
                description=pattern['description'],
                keywords=pattern['keywords'],
                estimated_potential=500 * pattern['severity'],
                action_items=[
                    f"Create comprehensive {pattern['type'].replace('_', ' ')}",
                    "Include structured data markup",
                    "Build internal linking strategy"
                ]
            )
            gaps.append(gap)

        return gaps

    def _analyze_local_gaps(self, niche: str, zip_code: str) -> List[GapOpportunity]:
        """Analyze local service gaps"""
        gaps = []

        # Local gap patterns
        local_patterns = [
            {
                'type': 'local_directory',
                'description': f"No quality local directory for {niche} in {zip_code}",
                'severity': 8,
                'action': "Build local business directory with reviews"
            },
            {
                'type': 'local_comparison',
                'description': f"Missing local comparison for {niche} providers in {zip_code}",
                'severity': 7,
                'action': "Create provider comparison with pricing"
            },
            {
                'type': 'local_guide',
                'description': f"No comprehensive local guide for {niche} in {zip_code}",
                'severity': 6,
                'action': "Build definitive local resource guide"
            }
        ]

        for pattern in local_patterns:
            gap = GapOpportunity(
                niche=niche,
                gap_type=pattern['type'],
                severity=pattern['severity'],
                description=pattern['description'],
                keywords=[
                    f"{niche} {zip_code}",
                    f"{niche} near {zip_code}",
                    f"best {niche} {zip_code}"
                ],
                estimated_potential=300 * pattern['severity'],
                action_items=[
                    pattern['action'],
                    "Collect local business data",
                    "Implement local schema markup"
                ]
            )
            gaps.append(gap)

        return gaps

    def find_micro_site_opportunities(
        self,
        niches: List[str],
        min_severity: int = 5
    ) -> List[Dict]:
        """
        Find micro-site opportunities across multiple niches

        Args:
            niches: List of niches to analyze
            min_severity: Minimum gap severity to include

        Returns:
            List of micro-site opportunities
        """
        opportunities = []

        for niche in niches:
            gaps = self.analyze_niche_gaps(niche)

            # Filter by severity
            significant_gaps = [g for g in gaps if g.severity >= min_severity]

            if len(significant_gaps) >= 2:
                # This niche has multiple significant gaps - micro-site opportunity
                opportunity = {
                    'niche': niche,
                    'gap_count': len(significant_gaps),
                    'total_severity': sum(g.severity for g in significant_gaps),
                    'top_gaps': [
                        {
                            'type': g.gap_type,
                            'severity': g.severity,
                            'keywords': g.keywords
                        }
                        for g in significant_gaps[:3]
                    ],
                    'estimated_traffic': sum(g.estimated_potential for g in significant_gaps),
                    'recommendation': self._generate_micro_site_recommendation(niche, significant_gaps)
                }
                opportunities.append(opportunity)

        # Sort by total severity
        opportunities.sort(key=lambda x: x['total_severity'], reverse=True)

        return opportunities

    def _generate_micro_site_recommendation(self, niche: str, gaps: List[GapOpportunity]) -> str:
        """Generate micro-site recommendation"""
        total_severity = sum(g.severity for g in gaps)

        if total_severity >= 25:
            return f"STRONG: Build dedicated micro-site for {niche}. Multiple high-severity gaps indicate low competition."
        elif total_severity >= 15:
            return f"MODERATE: {niche} shows promise. Start with content play, expand to full site if traction."
        else:
            return f"WEAK: {niche} has limited gaps. Consider as secondary target only."
