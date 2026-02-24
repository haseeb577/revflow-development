"""
RevPublish Performance Monitor - Simplified version
"""

from typing import Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Simple performance monitor"""
    
    def __init__(self):
        self.metrics = []
    
    def record(self, operation: str, duration_ms: float, success: bool = True, **metadata):
        """Record a metric"""
        metric = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(),
            "success": success,
            "metadata": metadata
        }
        self.metrics.append(metric)
        logger.debug(f"Recorded: {operation} - {duration_ms:.2f}ms")
    
    def get_stats(self) -> Dict:
        """Get basic statistics"""
        if not self.metrics:
            return {"total": 0}
        
        durations = [m["duration_ms"] for m in self.metrics]
        return {
            "total": len(self.metrics),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations)
        }


# Singleton
_monitor = None

def get_monitor() -> PerformanceMonitor:
    """Get global monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
