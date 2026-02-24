"""
YMYL Verification Checker
Verifies critical facts in YMYL content against source data
Prevents hallucinations in Your Money Your Life industries
"""
import re
from typing import Dict, List, Optional


class YMYLVerificationChecker:
    """
    Verifies critical facts in YMYL content against source truth
    
    YMYL Industries:
    - Healthcare: Licenses, credentials, medical claims
    - Legal: Bar numbers, case citations, legal advice
    - Finance: Licenses, regulatory compliance, investment claims
    - Home Services: Licenses, insurance, certifications
    """
    
    # YMYL industry classifications
    YMYL_INDUSTRIES = [
        'plumbing',
        'electrical',
        'hvac',
        'roofing',
        'legal',
        'medical',
        'healthcare',
        'finance',
        'investment',
        'insurance'
    ]
    
    # Critical fact patterns by industry
    FACT_PATTERNS = {
        'license': {
            'patterns': [
                r'license[#:\s]+([A-Z0-9-]+)',
                r'licensed[#:\s]+([A-Z0-9-]+)',
                r'lic[#:\s]+([A-Z0-9-]+)'
            ],
            'severity': 'critical'
        },
        'insurance': {
            'patterns': [
                r'\$([0-9,]+)\s+(?:million\s+)?(?:insurance|coverage)',
                r'([0-9,]+)\s+million\s+(?:insurance|coverage)'
            ],
            'severity': 'critical'
        },
        'certification': {
            'patterns': [
                r'certified\s+([A-Za-z0-9\s]+)',
                r'certification[#:\s]+([A-Z0-9-]+)'
            ],
            'severity': 'high'
        },
        'years_experience': {
            'patterns': [
                r'(\d+)\s+years?\s+(?:of\s+)?experience',
                r'over\s+(\d+)\s+years?'
            ],
            'severity': 'medium'
        },
        'phone': {
            'patterns': [
                r'\((\d{3})\)\s*(\d{3})-(\d{4})',
                r'(\d{3})-(\d{3})-(\d{4})'
            ],
            'severity': 'high'
        },
        'address': {
            'patterns': [
                r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)'
            ],
            'severity': 'medium'
        }
    }
    
    def verify_content(
        self,
        content: str,
        customer_profile: Dict,
        industry: str
    ) -> Dict:
        """
        Verify critical facts against source truth
        
        Args:
            content: Content to verify
            customer_profile: Source truth from RevScore IQ
            industry: Industry classification
        
        Returns:
            Dict with verification results and score
        """
        
        # Check if YMYL industry
        is_ymyl = industry.lower() in self.YMYL_INDUSTRIES
        
        if not is_ymyl:
            # Non-YMYL content - skip verification
            return {
                'verification_score': 100,
                'all_verified': True,
                'is_ymyl': False,
                'industry': industry,
                'failed_verifications': [],
                'verification_results': []
            }
        
        # Extract critical facts from content
        critical_facts = self._extract_critical_facts(content, industry)
        
        if not critical_facts:
            # No critical facts found - pass
            return {
                'verification_score': 100,
                'all_verified': True,
                'is_ymyl': True,
                'industry': industry,
                'failed_verifications': [],
                'verification_results': [],
                'note': 'No critical facts found to verify'
            }
        
        # Verify each fact against source
        verification_results = []
        
        for fact in critical_facts:
            verified = self._verify_against_source(
                fact=fact,
                source_data=customer_profile
            )
            
            verification_results.append({
                'fact': fact['text'],
                'fact_type': fact['type'],
                'content_value': fact['value'],
                'verified': verified['is_verified'],
                'source_value': verified.get('source_value'),
                'severity': fact['severity'],
                'reason': verified.get('reason')
            })
        
        # Calculate verification score
        total_facts = len(verification_results)
        
        # Weight by severity
        total_weight = 0
        verified_weight = 0
        
        severity_weights = {'critical': 3, 'high': 2, 'medium': 1}
        
        for result in verification_results:
            weight = severity_weights.get(result['severity'], 1)
            total_weight += weight
            
            if result['verified']:
                verified_weight += weight
        
        verification_score = (verified_weight / total_weight * 100) if total_weight > 0 else 100
        
        # Get failed verifications
        failed = [r for r in verification_results if not r['verified']]
        
        return {
            'verification_score': round(verification_score, 1),
            'all_verified': len(failed) == 0,
            'is_ymyl': True,
            'industry': industry,
            'total_facts_checked': total_facts,
            'failed_verifications': failed,
            'verification_results': verification_results
        }
    
    def _extract_critical_facts(self, content: str, industry: str) -> List[Dict]:
        """
        Extract critical facts based on industry
        
        Args:
            content: Content to extract from
            industry: Industry classification
        
        Returns:
            List of extracted facts
        """
        
        facts = []
        
        # Check each fact pattern
        for fact_type, config in self.FACT_PATTERNS.items():
            patterns = config['patterns']
            severity = config['severity']
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    # Get the full matched text
                    full_match = match.group(0)
                    
                    # Get the extracted value (first capture group or full match)
                    value = match.group(1) if match.groups() else full_match
                    
                    facts.append({
                        'type': fact_type,
                        'value': value.strip(),
                        'text': full_match,
                        'severity': severity,
                        'position': match.start()
                    })
        
        # Remove duplicates
        unique_facts = []
        seen = set()
        
        for fact in facts:
            key = (fact['type'], fact['value'])
            if key not in seen:
                seen.add(key)
                unique_facts.append(fact)
        
        return unique_facts
    
    def _verify_against_source(self, fact: Dict, source_data: Dict) -> Dict:
        """
        Verify fact against source data from RevScore IQ
        
        Args:
            fact: Fact to verify
            source_data: Source truth data
        
        Returns:
            Dict with verification result
        """
        
        fact_type = fact['type']
        content_value = fact['value']
        
        # Map fact types to source data fields
        source_field_map = {
            'license': ['license', 'license_number', 'contractor_license'],
            'insurance': ['insurance_amount', 'insurance_coverage', 'liability_insurance'],
            'certification': ['certifications', 'certificates', 'certified_in'],
            'years_experience': ['years_in_business', 'experience_years', 'years_experience'],
            'phone': ['phone', 'phone_number', 'contact_phone'],
            'address': ['address', 'business_address', 'street_address']
        }
        
        # Get possible source fields for this fact type
        possible_fields = source_field_map.get(fact_type, [])
        
        # Try to find matching source value
        source_value = None
        source_field = None
        
        for field in possible_fields:
            if field in source_data and source_data[field]:
                source_value = str(source_data[field])
                source_field = field
                break
        
        # If no source data available, cannot verify
        if source_value is None:
            return {
                'is_verified': False,
                'source_value': None,
                'reason': f'Source data not available (checked fields: {", ".join(possible_fields)})'
            }
        
        # Normalize for comparison
        content_normalized = self._normalize_value(content_value, fact_type)
        source_normalized = self._normalize_value(source_value, fact_type)
        
        # Check if match
        is_verified = content_normalized == source_normalized
        
        # For numeric values, allow small variance
        if fact_type in ['insurance', 'years_experience'] and not is_verified:
            is_verified = self._check_numeric_variance(
                content_normalized,
                source_normalized,
                tolerance=0.1  # 10% tolerance
            )
        
        return {
            'is_verified': is_verified,
            'source_value': source_value,
            'source_field': source_field,
            'reason': None if is_verified else f'Mismatch: content has "{content_value}", source has "{source_value}"'
        }
    
    def _normalize_value(self, value: str, fact_type: str) -> str:
        """
        Normalize value for comparison
        
        Args:
            value: Value to normalize
            fact_type: Type of fact
        
        Returns:
            Normalized value
        """
        
        # Remove common formatting
        normalized = value.strip().upper()
        
        # Remove separators
        normalized = normalized.replace('-', '').replace(' ', '').replace('_', '')
        
        # Remove currency symbols and commas for numbers
        if fact_type in ['insurance', 'years_experience']:
            normalized = normalized.replace('$', '').replace(',', '')
        
        return normalized
    
    def _check_numeric_variance(self, val1: str, val2: str, tolerance: float = 0.1) -> bool:
        """
        Check if two numeric values are within tolerance
        
        Args:
            val1: First value
            val2: Second value
            tolerance: Acceptable variance (0.1 = 10%)
        
        Returns:
            True if within tolerance
        """
        
        try:
            num1 = float(val1)
            num2 = float(val2)
            
            if num2 == 0:
                return num1 == 0
            
            variance = abs(num1 - num2) / num2
            
            return variance <= tolerance
        
        except (ValueError, TypeError):
            return False
    
    def batch_verify(
        self,
        items: List[Dict],
        customer_profiles: Dict[str, Dict],
        industry_map: Dict[str, str]
    ) -> List[Dict]:
        """
        Batch verify multiple content items
        
        Args:
            items: List of dicts with 'id' and 'content'
            customer_profiles: Map of content_id to customer profile
            industry_map: Map of content_id to industry
        
        Returns:
            List of verification results
        """
        
        results = []
        
        for item in items:
            content_id = item.get('id', 'unknown')
            content = item.get('content', '')
            
            customer_profile = customer_profiles.get(content_id, {})
            industry = industry_map.get(content_id, 'unknown')
            
            result = self.verify_content(content, customer_profile, industry)
            result['content_id'] = content_id
            
            results.append(result)
        
        return results
