"""
Humanizer Validator - Implements the 3-tier validation framework
Tier 1: Kill List (Auto-Reject)
Tier 2: Proof Required (Manual Review)
Tier 3: Pattern Replacement (Auto-Fix)
Plus: E-E-A-T and GEO compliance checking
"""
import re
import yaml
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import textstat
from loguru import logger

from ..models import (
    HumanizerValidationResult,
    Tier1Issue, Tier2Issue, Tier3Issue,
    EEATScore, GEOScore, StructuralScore,
    ValidationStatus
)


class HumanizerValidator:
    """
    Comprehensive content validation using the Sabrina Ramonov framework
    """
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "content_rules.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        logger.info("Humanizer Validator initialized")
    
    async def validate(self, content: str, title: str = "", keywords: List[str] = None) -> HumanizerValidationResult:
        """
        Run complete validation on content
        
        Returns comprehensive validation result with all scoring
        """
        logger.info(f"Validating content ({len(content)} chars)")
        
        # Tier 1: Kill List scan (Critical)
        tier1_issues = await self._scan_tier1(content)
        
        # Tier 2: Proof required scan (Major)
        tier2_issues = await self._scan_tier2(content)
        
        # Tier 3: Pattern replacement scan (Minor - auto-fixable)
        tier3_issues = await self._scan_tier3(content)
        
        # E-E-A-T compliance
        eeat_score = await self._check_eeat(content)
        
        # GEO optimization
        geo_score = await self._check_geo(content)
        
        # Structural compliance
        structural_score = await self._check_structural(content, keywords or [])
        
        # Calculate final score
        final_score = await self._calculate_final_score(
            tier1_issues, tier2_issues, tier3_issues,
            eeat_score, geo_score, structural_score
        )
        
        # Determine status
        status = await self._determine_status(
            tier1_issues, tier2_issues, tier3_issues, final_score
        )
        
        result = HumanizerValidationResult(
            tier1_issues=tier1_issues,
            tier2_issues=tier2_issues,
            tier3_issues=tier3_issues,
            eeat_score=eeat_score,
            geo_score=geo_score,
            structural_score=structural_score,
            final_score=final_score,
            status=status,
            can_auto_fix=(len(tier1_issues) == 0 and len(tier2_issues) == 0 and len(tier3_issues) > 0),
            needs_manual_review=(len(tier2_issues) > 0),
            issues_summary={
                "tier1": len(tier1_issues),
                "tier2": len(tier2_issues),
                "tier3": len(tier3_issues)
            },
            estimated_cost_usd=0.03  # From config
        )
        
        logger.info(f"Validation complete: {status.value}, Score: {final_score}")
        
        return result
    
    async def _scan_tier1(self, content: str) -> List[Tier1Issue]:
        """
        Scan for Tier 1 kill words (Auto-Reject)
        """
        issues = []
        content_lower = content.lower()
        
        # Check kill words
        for category in ['verbs', 'adjectives', 'adverbs', 'phrases']:
            kill_words = self.config['tier1_kill_words'].get(category, [])
            
            for word in kill_words:
                # Use word boundaries for words, regular search for phrases
                if len(word.split()) == 1:
                    pattern = rf'\b{re.escape(word)}\b'
                else:
                    pattern = re.escape(word)
                
                for match in re.finditer(pattern, content_lower, re.IGNORECASE):
                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]
                    
                    issues.append(Tier1Issue(
                        word=word,
                        category=category,
                        context=context,
                        position=match.start()
                    ))
        
        # Check forbidden patterns
        for pattern_rule in self.config['tier1_kill_words']['forbidden_patterns']:
            pattern = pattern_rule['pattern']
            description = pattern_rule['description']
            
            for match in re.finditer(pattern, content_lower, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                issues.append(Tier1Issue(
                    word=match.group(),
                    category='forbidden_pattern',
                    context=context,
                    position=match.start()
                ))
        
        logger.info(f"Tier 1 scan: {len(issues)} critical issues found")
        return issues
    
    async def _scan_tier2(self, content: str) -> List[Tier2Issue]:
        """
        Scan for Tier 2 proof-required words
        These are only issues if they appear WITHOUT substantiation
        """
        issues = []
        content_lower = content.lower()
        
        tier2_words = self.config['tier2_proof_required']['words']
        proof_patterns = self.config['tier2_proof_required']['proof_patterns']
        proximity = self.config['tier2_proof_required']['proximity_words']
        
        for trigger_word in tier2_words:
            pattern = rf'\b{re.escape(trigger_word)}\b'
            
            for match in re.finditer(pattern, content_lower, re.IGNORECASE):
                # Get surrounding context (proximity words)
                words = content_lower.split()
                match_word_index = len(content_lower[:match.start()].split())
                
                start_idx = max(0, match_word_index - proximity)
                end_idx = min(len(words), match_word_index + proximity)
                
                surrounding_text = ' '.join(words[start_idx:end_idx])
                
                # Check if any proof pattern exists in surrounding text
                has_proof = False
                for proof_pattern in proof_patterns:
                    if re.search(proof_pattern, surrounding_text):
                        has_proof = True
                        break
                
                if not has_proof:
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    context = content[start:end]
                    
                    issues.append(Tier2Issue(
                        trigger_word=trigger_word,
                        context=context,
                        position=match.start(),
                        missing_proof="number, percentage, or specific outcome",
                        suggestion=f'Add specific proof after "{trigger_word}" (e.g., "We {trigger_word} load time from 4.2s to 1.1s")'
                    ))
        
        logger.info(f"Tier 2 scan: {len(issues)} proof-required issues found")
        return issues
    
    async def _scan_tier3(self, content: str) -> List[Tier3Issue]:
        """
        Scan for Tier 3 patterns that should be replaced
        These are auto-fixable
        """
        issues = []
        
        replacements = self.config['tier3_replacements']
        
        for rule in replacements:
            pattern = rule['pattern']
            replacement = rule['replacement']
            description = rule['description']
            
            for match in re.finditer(pattern, content, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                issues.append(Tier3Issue(
                    pattern=description,
                    match=match.group(),
                    replacement=replacement,
                    context=context,
                    position=match.start()
                ))
        
        logger.info(f"Tier 3 scan: {len(issues)} pattern issues found")
        return issues
    
    async def _check_eeat(self, content: str) -> EEATScore:
        """
        Check E-E-A-T compliance
        """
        content_lower = content.lower()
        
        # Experience markers
        experience_patterns = self.config['eeat_requirements']['experience']['patterns']
        experience_markers = []
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            experience_markers.extend(matches)
        
        # Score: 10 points per marker, max 30
        experience_score = min(30, len(experience_markers) * 10)
        
        # Expertise indicators
        expertise_indicators = self.config['eeat_requirements']['expertise']['indicators']
        expertise_found = []
        
        for indicator in expertise_indicators:
            if re.search(indicator, content_lower, re.IGNORECASE):
                expertise_found.append(indicator)
        
        # Score: 15 points per indicator, max 45
        expertise_score = min(45, len(expertise_found) * 15)
        
        # Authoritativeness - check for unique data/research
        authority_keywords = self.config['eeat_requirements']['authoritativeness']['citation_worthy']
        authority_count = sum(1 for kw in authority_keywords if kw in content_lower)
        authoritativeness_score = min(15, authority_count * 5)
        
        # Trustworthiness - voice check
        first_person_count = len(re.findall(r'\b(we|i|our|my)\b', content_lower))
        third_person_passive = len(re.findall(r'\b(it is|there are|one should)\b', content_lower))
        
        voice_check_passed = first_person_count > third_person_passive
        trustworthiness_score = 10 if voice_check_passed else 0
        
        total = experience_score + expertise_score + authoritativeness_score + trustworthiness_score
        
        issues = []
        if experience_score < 10:
            issues.append("Missing personal experience markers (e.g., 'In my experience...', 'I've found...')")
        if expertise_score < 15:
            issues.append("Insufficient expertise indicators")
        if not voice_check_passed:
            issues.append("Content uses passive/third-person voice instead of first-person")
        
        return EEATScore(
            experience_score=experience_score,
            expertise_score=expertise_score,
            authoritativeness_score=authoritativeness_score,
            trustworthiness_score=trustworthiness_score,
            total_score=total,
            experience_markers_found=experience_markers,
            expertise_indicators_found=expertise_found,
            voice_check_passed=voice_check_passed,
            issues=issues
        )
    
    async def _check_geo(self, content: str) -> GEOScore:
        """
        Check GEO (Generative Engine Optimization) compliance
        """
        issues = []
        score = 100
        
        # Check answer frontloading (first 100 words)
        words = content.split()
        first_100_words = ' '.join(words[:100])
        
        # Simple heuristic: Should contain key information
        # Check for presence of numbers, specific terms, or definitions
        has_answer = bool(re.search(r'\d+|is\s+(?:a|an|the)', first_100_words))
        
        if not has_answer:
            issues.append("Answer not front-loaded in first 100 words")
            score -= 30
        
        # Check for FAQ section
        faq_pattern = r'\*\*[^*]+\?\*\*|<h\d>[^<]+\?</h\d>'
        faq_matches = re.findall(faq_pattern, content)
        faq_count = len(faq_matches)
        
        faq_present = faq_count >= 7
        
        if not faq_present:
            issues.append(f"FAQ section missing or insufficient ({faq_count} questions, need 7-10)")
            score -= 40
        elif faq_count > 10:
            issues.append(f"Too many FAQ questions ({faq_count}, recommended 7-10)")
            score -= 10
        
        # Check snippet optimization (headings, structure)
        h2_h3_count = len(re.findall(r'<h[23]>', content))
        forbidden_headings = re.findall(r'<h[1456]>', content)
        
        snippet_optimized = h2_h3_count > 0 and len(forbidden_headings) == 0
        
        if not snippet_optimized:
            issues.append("Heading structure not optimized for snippets (use H2/H3 only)")
            score -= 20
        
        return GEOScore(
            answer_frontloaded=has_answer,
            faq_present=faq_present,
            faq_count=faq_count,
            snippet_optimized=snippet_optimized,
            score=max(0, score),
            issues=issues
        )
    
    async def _check_structural(self, content: str, keywords: List[str]) -> StructuralScore:
        """
        Check structural compliance (reading level, formatting, SEO)
        """
        issues = []
        
        # Reading level (Flesch-Kincaid)
        reading_level = textstat.flesch_kincaid_grade(content)
        target_min = self.config['structural_requirements']['reading_level']['flesch_kincaid_min']
        target_max = self.config['structural_requirements']['reading_level']['flesch_kincaid_max']
        
        if reading_level < target_min or reading_level > target_max:
            issues.append(f"Reading level {reading_level:.1f} outside target range ({target_min}-{target_max})")
        
        # Paragraph length (approximate)
        paragraphs = content.split('\n\n')
        avg_paragraph_length = np.mean([len(p.split('\n')) for p in paragraphs if p.strip()])
        
        if avg_paragraph_length > 3:
            issues.append(f"Average paragraph length ({avg_paragraph_length:.1f} lines) exceeds 3 lines")
        
        # Sentence length
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = np.mean([len(s.split()) for s in sentences]) if sentences else 0
        
        # Keyword density
        keyword_density = 0.0
        if keywords:
            total_words = len(content.split())
            keyword_count = sum(content.lower().count(kw.lower()) for kw in keywords)
            keyword_density = keyword_count / total_words if total_words > 0 else 0
            
            if keyword_density < 0.010 or keyword_density > 0.015:
                issues.append(f"Keyword density {keyword_density:.1%} outside target (1.0-1.5%)")
        
        # Em dashes
        em_dashes_found = content.count('—')
        if em_dashes_found > 0:
            issues.append(f"Found {em_dashes_found} em dashes (—) - must replace with commas or colons")
        
        # Forbidden headings
        forbidden_headings = re.findall(r'<h[1456]>', content)
        if forbidden_headings:
            issues.append(f"Found forbidden heading levels: {', '.join(set(forbidden_headings))}")
        
        # Naked URLs
        naked_urls = len(re.findall(r'https?://[^\s<>"]+', content))
        if naked_urls > 0:
            issues.append(f"Found {naked_urls} naked URLs - must use anchor text")
        
        # Calculate score
        score = 100
        score -= len(issues) * 5  # 5 points per issue
        
        return StructuralScore(
            reading_level=reading_level,
            avg_paragraph_length=avg_paragraph_length,
            avg_sentence_length=avg_sentence_length,
            keyword_density=keyword_density,
            em_dashes_found=em_dashes_found,
            forbidden_headings=forbidden_headings,
            naked_urls=naked_urls,
            score=max(0, score),
            issues=issues
        )
    
    async def _calculate_final_score(
        self,
        tier1_issues: List[Tier1Issue],
        tier2_issues: List[Tier2Issue],
        tier3_issues: List[Tier3Issue],
        eeat_score: EEATScore,
        geo_score: GEOScore,
        structural_score: StructuralScore
    ) -> int:
        """
        Calculate final quality score (0-100)
        """
        # Start at 100
        score = 100
        
        # Tier 1 = instant fail
        if tier1_issues:
            return 0
        
        # Tier 2 = major penalty
        score -= len(tier2_issues) * 25
        
        # Tier 3 = minor penalty
        score -= len(tier3_issues) * 5
        
        # Add weighted component scores
        # E-E-A-T: 20% weight
        score += (eeat_score.total_score / 100) * 20
        
        # GEO: 10% weight
        score += (geo_score.score / 100) * 10
        
        # Structural: 5% weight
        score += (structural_score.score / 100) * 5
        
        return max(0, min(100, int(score)))
    
    async def _determine_status(
        self,
        tier1_issues: List[Tier1Issue],
        tier2_issues: List[Tier2Issue],
        tier3_issues: List[Tier3Issue],
        final_score: int
    ) -> ValidationStatus:
        """
        Determine validation status
        """
        # Critical fail
        if tier1_issues:
            return ValidationStatus.REJECT
        
        # Manual review needed
        if tier2_issues:
            return ValidationStatus.MANUAL_REVIEW
        
        # Can auto-fix
        if tier3_issues and final_score >= 70:
            return ValidationStatus.AUTO_FIXED
        
        # Passes
        if final_score >= 70:
            return ValidationStatus.PASS
        
        # Below threshold
        return ValidationStatus.REJECT
