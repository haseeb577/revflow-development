"""
RevSPY™ Report Templates
Convenience functions for report generation
"""
from .generator import ReportGenerator

_generator = ReportGenerator()

def generate_prospect_report(prospect_place_id: str, market: str):
    """Generate prospect competitive analysis"""
    return _generator.generate_prospect_report(prospect_place_id, market)

def generate_monthly_client_report(client_place_id: str, market: str):
    """Generate monthly client progress report"""
    return _generator.generate_monthly_client_report(client_place_id, market)

def generate_market_opportunity_briefing(market: str, min_opportunity_score: int = 70):
    """Generate market opportunity analysis"""
    # TODO: Implement market opportunity analysis
    pass

def generate_competitive_benchmark(market: str, category: str):
    """Generate competitive benchmark tracking"""
    # TODO: Implement competitive benchmark tracking
    pass
