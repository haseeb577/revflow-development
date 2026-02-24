"""
AI Detection Engine
Multiple methods to detect AI-generated content
"""
from typing import Dict, Any
import re

class AIDetector:
    """
    Detects AI-generated content using multiple methods
    """
    
    # AI indicators
    AI_PHRASES = [
        "as an ai", "i don't have personal", "i cannot",
        "it's important to note", "delve into",
        "comprehensive guide", "navigate the landscape",
        "in today's digital age", "to summarize"
    ]
    
    def detect(self, content: str) -> Dict[str, Any]:
        """
        Detect if content is AI-generated
        
        Returns:
            {
                "is_ai_generated": bool,
                "confidence": float,
                "probability": float,
                "method": str,
                "details": Dict
            }
        """
        content_lower = content.lower()
        
        # Method 1: Pattern matching
        ai_phrase_count = sum(1 for phrase in self.AI_PHRASES if phrase in content_lower)
        
        # Method 2: Sentence structure uniformity (simple check)
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        if sentences:
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            length_variance = sum(abs(len(s.split()) - avg_length) for s in sentences) / len(sentences)
            uniformity_score = 1 - min(1, length_variance / avg_length)
        else:
            uniformity_score = 0
        
        # Calculate probability
        pattern_score = min(1, ai_phrase_count / 3)  # 3+ AI phrases = likely AI
        
        probability = (pattern_score * 0.7 + uniformity_score * 0.3)
        
        is_ai = probability > 0.6
        confidence = abs(probability - 0.5) * 2  # How far from uncertain
        
        return {
            "is_ai_generated": is_ai,
            "confidence": round(confidence, 2),
            "probability": round(probability, 2),
            "method": "pattern_and_structure",
            "details": {
                "ai_phrases_found": ai_phrase_count,
                "sentence_uniformity": round(uniformity_score, 2),
                "pattern_score": round(pattern_score, 2)
            }
        }
