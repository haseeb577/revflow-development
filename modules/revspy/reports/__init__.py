"""
RevSPY™ GBP Intelligence - Report Generation Module
Automated competitive analysis reports for prospects and clients
"""
from .generator import ReportGenerator
from .templates import (
    generate_prospect_report,
    generate_monthly_client_report,
    generate_market_opportunity_briefing,
    generate_competitive_benchmark
)

__all__ = [
    'ReportGenerator',
    'generate_prospect_report',
    'generate_monthly_client_report',
    'generate_market_opportunity_briefing',
    'generate_competitive_benchmark'
]
