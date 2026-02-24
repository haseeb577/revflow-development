"""
RevPublish Batch Processor - Simplified version
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Simple batch processor for parallel content generation"""
    
    def __init__(self, batch_size: int = 3):
        self.batch_size = batch_size
    
    async def process_batch(
        self,
        items: List[Any],
        processor_func: Callable
    ) -> Dict[str, Any]:
        """Process items in batches"""
        
        start_time = datetime.now()
        all_results = []
        
        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        logger.info(f"Processing {len(items)} items in {len(batches)} batches")
        
        for batch_num, batch in enumerate(batches, 1):
            logger.info(f"Batch {batch_num}/{len(batches)}")
            
            # Create parallel tasks
            tasks = [processor_func(item) for item in batch]
            
            # Execute in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return {
            "total": len(all_results),
            "elapsed_seconds": elapsed,
            "results": all_results
        }
