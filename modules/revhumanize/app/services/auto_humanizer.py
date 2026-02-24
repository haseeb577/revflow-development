"""Auto-Humanization Service - Attempts to fix common issues"""
from typing import List, Dict, Any, Tuple
import re

class AutoHumanizer:
    """Automatically fixes common content issues"""
    
    def attempt_fixes(self, content: str, issues: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """
        Attempt to fix issues automatically
        Returns: (fixed_content, changes_made)
        """
        fixed_content = content
        changes = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "long_sentences":
                fixed_content, changed = self._fix_long_sentences(fixed_content)
                if changed:
                    changes.append("Split long sentences for readability")
            
            elif issue_type == "passive_voice":
                fixed_content, changed = self._reduce_passive_voice(fixed_content)
                if changed:
                    changes.append("Converted passive voice to active")
            
            elif issue_type == "repetitive_words":
                fixed_content, changed = self._fix_repetition(fixed_content)
                if changed:
                    changes.append("Reduced word repetition")
        
        return fixed_content, changes
    
    def _fix_long_sentences(self, content: str) -> Tuple[str, bool]:
        """Split sentences longer than 25 words"""
        sentences = content.split('. ')
        changed = False
        fixed_sentences = []
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 25:
                # Simple split at 'and' or 'but'
                mid_point = len(words) // 2
                for i, word in enumerate(words[mid_point-5:mid_point+5], start=mid_point-5):
                    if word.lower() in ['and', 'but', 'or']:
                        first_half = ' '.join(words[:i])
                        second_half = ' '.join(words[i+1:])
                        fixed_sentences.append(first_half + '.')
                        fixed_sentences.append(second_half.capitalize())
                        changed = True
                        break
                else:
                    fixed_sentences.append(sentence)
            else:
                fixed_sentences.append(sentence)
        
        return '. '.join(fixed_sentences), changed
    
    def _reduce_passive_voice(self, content: str) -> Tuple[str, bool]:
        """Basic passive voice detection and conversion"""
        # Simple pattern: "was/were + past participle"
        passive_pattern = r'\b(was|were|is|are)\s+(\w+ed)\b'
        if re.search(passive_pattern, content):
            # This is a simplified example - real implementation would be more sophisticated
            return content, False
        return content, False
    
    def _fix_repetition(self, content: str) -> Tuple[str, bool]:
        """Remove obvious word repetition"""
        words = content.split()
        fixed_words = []
        prev_word = None
        changed = False
        
        for word in words:
            if word.lower() != (prev_word or '').lower():
                fixed_words.append(word)
            else:
                changed = True
            prev_word = word
        
        return ' '.join(fixed_words), changed
    
    def can_auto_fix(self, issues: List[Dict[str, Any]]) -> bool:
        """Determine if issues can be auto-fixed"""
        auto_fixable = ["long_sentences", "repetitive_words", "passive_voice"]
        
        for issue in issues:
            if issue.get("severity") == "critical":
                return False
            if issue.get("type") not in auto_fixable:
                return False
        
        return True
