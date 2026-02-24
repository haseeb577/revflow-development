"""
Voice Consistency Checker
Prevents voice modality bleeding during ensemble humanization
"""
import re
from typing import Dict, List


class VoiceConsistencyChecker:
    """
    Validates that humanized content maintains target voice modality
    
    Prevents mixing of voice patterns (Partner → Peer → Professor)
    that can occur during ensemble LLM humanization
    """
    
    VOICE_PATTERNS = {
        'partner': {
            'allowed': [
                'directive_verbs',  # "Contact", "Schedule", "Call"
                'confident_statements',  # "We provide", "Our team ensures"
                'action_oriented'  # "Get started", "Reach out"
            ],
            'forbidden': [
                'empathetic_peer',  # "I understand how frustrating..."
                'academic_professor',  # "One might consider...", "It is worth noting..."
                'tentative_language'  # "Perhaps", "Maybe", "Possibly"
            ]
        },
        'peer': {
            'allowed': [
                'conversational_tone',
                'empathetic_phrases',
                'relatable_examples'
            ],
            'forbidden': [
                'overly_formal',
                'sales_language',
                'academic_jargon'
            ]
        },
        'professor': {
            'allowed': [
                'technical_terminology',
                'explanatory_structures',
                'educational_framing'
            ],
            'forbidden': [
                'sales_pressure',
                'overly_casual',
                'slang'
            ]
        }
    }
    
    # Pattern detection rules
    PATTERN_DETECTORS = {
        'empathetic_peer': [
            'I understand how',
            'I know it can be',
            'That must be frustrating',
            'I can imagine',
            'I feel you',
            'I get it'
        ],
        'academic_professor': [
            'One might consider',
            'It is worth noting',
            'As previously mentioned',
            'In conclusion',
            'Furthermore',
            'Moreover',
            'Subsequently',
            'Aforementioned'
        ],
        'tentative_language': [
            'Perhaps',
            'Maybe',
            'Possibly',
            'It could be',
            'One option might be',
            'You might want to',
            'Consider possibly',
            'Potentially'
        ],
        'overly_formal': [
            'Herein',
            'Whereby',
            'Notwithstanding',
            'Pursuant to',
            'Heretofore'
        ],
        'sales_language': [
            'Limited time offer',
            'Act now',
            'Don\'t miss out',
            'Exclusive deal',
            'Best price guaranteed'
        ],
        'academic_jargon': [
            'Synergize',
            'Paradigm shift',
            'Utilize',
            'Leverage',
            'Optimization'
        ],
        'sales_pressure': [
            'Buy now',
            'Limited slots',
            'Only X remaining',
            'Hurry',
            'Don\'t wait'
        ],
        'overly_casual': [
            'Gonna',
            'Wanna',
            'Kinda',
            'Sorta',
            'Ya know'
        ],
        'slang': [
            'Cool beans',
            'No prob',
            'Totes',
            'Lit',
            'Fire'
        ]
    }
    
    def check_voice_consistency(
        self,
        content: str,
        target_voice: str = 'partner'
    ) -> Dict:
        """
        Analyze content for voice consistency violations
        
        Args:
            content: HTML or text content to check
            target_voice: Target voice modality ('partner', 'peer', 'professor')
        
        Returns:
            Dict with consistency score, violations, and pass/fail status
        """
        
        if target_voice not in self.VOICE_PATTERNS:
            raise ValueError(f"Unknown voice: {target_voice}. Must be one of {list(self.VOICE_PATTERNS.keys())}")
        
        # Tokenize content
        sentences = self._split_sentences(content)
        
        if not sentences:
            return {
                'consistency_score': 100,
                'violations': [],
                'passed': True,
                'target_voice': target_voice,
                'total_sentences': 0
            }
        
        # Check each sentence for forbidden patterns
        violations = []
        
        forbidden_patterns = self.VOICE_PATTERNS[target_voice]['forbidden']
        
        for idx, sentence in enumerate(sentences):
            for pattern_type in forbidden_patterns:
                if self._contains_pattern(sentence, pattern_type):
                    violations.append({
                        'sentence_idx': idx,
                        'sentence': sentence[:100] + ('...' if len(sentence) > 100 else ''),
                        'pattern_type': pattern_type,
                        'severity': 'high',
                        'suggestion': self._get_fix_suggestion(pattern_type, target_voice)
                    })
        
        # Calculate consistency score
        total_sentences = len(sentences)
        violation_count = len(violations)
        consistency_score = ((total_sentences - violation_count) / total_sentences) * 100
        
        return {
            'consistency_score': round(consistency_score, 1),
            'violations': violations,
            'passed': consistency_score >= 80,
            'target_voice': target_voice,
            'total_sentences': total_sentences,
            'violation_count': violation_count
        }
    
    def _contains_pattern(self, sentence: str, pattern_type: str) -> bool:
        """
        Check if sentence contains forbidden pattern
        
        Args:
            sentence: Sentence text to check
            pattern_type: Type of pattern to look for
        
        Returns:
            True if pattern found, False otherwise
        """
        
        if pattern_type not in self.PATTERN_DETECTORS:
            return False
        
        sentence_lower = sentence.lower()
        
        for pattern in self.PATTERN_DETECTORS[pattern_type]:
            if pattern.lower() in sentence_lower:
                return True
        
        return False
    
    def _get_fix_suggestion(self, pattern_type: str, target_voice: str) -> str:
        """
        Get suggestion for fixing voice consistency violation
        """
        
        suggestions = {
            'partner': {
                'empathetic_peer': 'Use direct, confident statements instead of empathetic language',
                'academic_professor': 'Replace formal language with clear, actionable directives',
                'tentative_language': 'Replace tentative words with confident, decisive language'
            },
            'peer': {
                'overly_formal': 'Use conversational, friendly language',
                'sales_language': 'Focus on helping, not selling',
                'academic_jargon': 'Use plain language and relatable examples'
            },
            'professor': {
                'sales_pressure': 'Focus on education, not persuasion',
                'overly_casual': 'Maintain professional, educational tone',
                'slang': 'Use proper terminology and formal language'
            }
        }
        
        return suggestions.get(target_voice, {}).get(pattern_type, 'Review and revise for voice consistency')
    
    def _split_sentences(self, content: str) -> List[str]:
        """
        Split content into sentences
        
        Args:
            content: HTML or text content
        
        Returns:
            List of sentences
        """
        # Remove HTML tags first
        text = re.sub(r'<[^>]+>', '', content)
        
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        return sentences
    
    def batch_check(self, contents: List[Dict[str, str]], target_voice: str = 'partner') -> List[Dict]:
        """
        Batch check multiple content items
        
        Args:
            contents: List of dicts with 'content' and optional 'id' keys
            target_voice: Target voice for all items
        
        Returns:
            List of check results with IDs
        """
        results = []
        
        for item in contents:
            content_id = item.get('id', 'unknown')
            content = item.get('content', '')
            
            result = self.check_voice_consistency(content, target_voice)
            result['content_id'] = content_id
            
            results.append(result)
        
        return results
