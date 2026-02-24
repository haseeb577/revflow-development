"""
RevSPY™ Email Template Generator
Auto-generates personalized sales emails from competitive analysis
"""
from typing import Dict
from datetime import datetime

class EmailTemplateGenerator:
    """Generate personalized sales emails from report data"""
    
    def generate_prospect_email(self, report: Dict, recipient_name: str = None) -> Dict:
        """
        Generate initial outreach email for prospects
        Uses competitive analysis data to create personalized pitch
        """
        prospect = report['prospect']
        market = report['market']
        gaps = report['gaps']
        recommendation = report['recommendation']
        competitors = report.get('top_competitors', [])
        
        # Personalize name
        first_name = recipient_name or "there"
        
        # Build subject line
        subject = self._generate_subject_line(prospect, market)
        
        # Build email body
        body = self._generate_prospect_body(
            first_name, prospect, market, gaps, recommendation, competitors
        )
        
        return {
            "subject": subject,
            "body": body,
            "template_type": "prospect_outreach",
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_monthly_client_email(self, report: Dict, recipient_name: str = None) -> Dict:
        """
        Generate monthly progress email for existing clients
        """
        client = report['client']
        changes = report.get('monthly_changes')
        performance = report.get('performance')
        
        first_name = recipient_name or client.get('business_name', 'there')
        
        subject = f"📊 Your Monthly GBP Report - {report.get('report_month')}"
        
        body = self._generate_client_body(first_name, client, changes, performance)
        
        return {
            "subject": subject,
            "body": body,
            "template_type": "monthly_client_report",
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_subject_line(self, prospect: Dict, market: Dict) -> str:
        """Generate attention-grabbing subject line"""
        rank = prospect.get('competitor_rank')
        total = market.get('total_competitors')
        business = prospect.get('business_name')
        
        if rank == 1:
            return f"🏆 {business} - You're #1, but here's the threat..."
        elif rank <= 3:
            return f"📊 {business} - Ranking #{rank} of {total}. Close the gap?"
        elif rank <= 10:
            return f"⚠️ {business} - #{rank} of {total}. Here's how to break top 3"
        else:
            return f"💡 {business} - Found {len(market.get('total_competitors', 0))} gaps to exploit"
    
    def _generate_prospect_body(self, name: str, prospect: Dict, market: Dict, 
                                  gaps: Dict, recommendation: Dict, competitors: list) -> str:
        """Generate personalized prospect email body"""
        
        business = prospect.get('business_name')
        rank = prospect.get('competitor_rank')
        total = market.get('total_competitors')
        rating = prospect.get('rating', 0)
        reviews = prospect.get('review_count', 0)
        health = prospect.get('gbp_health_score', 0)
        
        # Gap analysis
        review_gap = abs(int(gaps.get('reviews', 0)))
        photo_gap = abs(int(gaps.get('photos', 0)))
        rating_gap = abs(round(gaps.get('rating', 0), 1))
        
        email = f"""Hi {name},

I ran {business}'s Google Business Profile through our competitive intelligence system.

Here's what I found:

YOUR POSITION:
• Current Rank: #{rank} out of {total} competitors
• GBP Health Score: {health}/100
• Rating: {rating} stars ({reviews} reviews)

"""
        
        # Add competitor comparison if available
        if competitors:
            email += "MARKET LEADERS (Top 3):\n"
            for i, comp in enumerate(competitors[:3], 1):
                email += f"{i}. {comp['business_name']}: {comp.get('gbp_health_score', 0)}/100 - {comp['rating']} stars ({comp['review_count']} reviews)\n"
            email += "\n"
        
        # Add gaps
        email += "THE GAP:\n"
        if review_gap > 0:
            email += f"✗ Reviews: You're {review_gap} reviews behind market average\n"
        if photo_gap > 0:
            email += f"✗ Photos: You need {photo_gap} more photos to match competitors\n"
        if rating_gap > 0:
            email += f"✗ Rating: {rating_gap} stars behind market leaders\n"
        
        email += f"\n"
        
        # Add recommendation
        priority = recommendation.get('priority')
        message = recommendation.get('message')
        investment = recommendation.get('investment')
        
        email += f"THE OPPORTUNITY:\n{message}\n\n"
        email += f"Recommended Investment: {investment}\n\n"
        
        # CTA
        if rank <= 3:
            email += "Want to defend your position? Let's talk strategy.\n\n"
        else:
            target_rank = max(1, rank - 5)
            email += f"I can show you exactly how to move from #{rank} to #{target_rank} in 90 days.\n\n"
        
        email += "Would you like to see the complete analysis?\n\n"
        email += "Best,\n[Your Name]\n\n"
        email += f"P.S. I also found {total - 3} geographic gaps in your market where competitors are weak. These represent immediate opportunities."
        
        return email
    
    def _generate_client_body(self, name: str, client: Dict, changes: Dict, performance: str) -> str:
        """Generate monthly client report email"""
        
        business = client.get('business_name')
        current = client.get('current_stats', {})
        
        email = f"""Hi {name},

Here's your monthly GBP performance report for {business}.

CURRENT STATUS:
• Rank: #{current.get('rank')}
• Rating: {current.get('rating')} stars
• Reviews: {current.get('reviews')}
• Health Score: {current.get('health_score')}/100

"""
        
        if changes:
            email += "THIS MONTH'S CHANGES:\n"
            
            rank_change = changes.get('rank', 0)
            if rank_change > 0:
                email += f"📈 Moved UP {rank_change} positions!\n"
            elif rank_change < 0:
                email += f"📉 Dropped {abs(rank_change)} positions\n"
            else:
                email += f"➡️  Rank maintained\n"
            
            reviews_gained = changes.get('reviews', 0)
            if reviews_gained > 0:
                email += f"⭐ Gained {reviews_gained} new reviews\n"
            
            score_change = changes.get('score', 0)
            if score_change > 0:
                email += f"✅ Health score improved by {score_change} points\n"
            
            email += f"\n"
        
        email += f"OVERALL PERFORMANCE: {performance}\n\n"
        
        if performance in ["EXCELLENT", "GOOD"]:
            email += "Keep up the great work! You're on track to dominate your market.\n"
        elif performance == "FAIR":
            email += "We're making progress. Let's discuss ways to accelerate growth.\n"
        else:
            email += "We need to adjust our strategy. Let's schedule a call to discuss.\n"
        
        email += "\nQuestions? Reply to this email or schedule a call.\n\n"
        email += "Best,\n[Your Name]"
        
        return email


# Convenience functions
def generate_prospect_email(report: Dict, recipient_name: str = None) -> Dict:
    """Generate prospect outreach email"""
    generator = EmailTemplateGenerator()
    return generator.generate_prospect_email(report, recipient_name)


def generate_client_email(report: Dict, recipient_name: str = None) -> Dict:
    """Generate monthly client email"""
    generator = EmailTemplateGenerator()
    return generator.generate_monthly_client_email(report, recipient_name)
