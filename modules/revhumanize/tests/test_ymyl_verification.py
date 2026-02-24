"""
Tests for YMYL Verification Checker
"""
import pytest
from app.validators.ymyl_checker import YMYLVerificationChecker


class TestYMYLVerificationChecker:
    """Test suite for YMYL fact verification"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.checker = YMYLVerificationChecker()
    
    def test_license_match(self):
        """Test: License number matches source data"""
        content = "Licensed plumber #TX-12345"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
        assert result['verification_score'] == 100
        assert result['is_ymyl'] == True
        assert len(result['failed_verifications']) == 0
    
    def test_license_mismatch(self):
        """Test: License number doesn't match source data"""
        content = "Licensed plumber #TX-99999"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == False
        assert result['verification_score'] < 100
        assert len(result['failed_verifications']) > 0
        assert 'Mismatch' in result['failed_verifications'][0]['reason']
    
    def test_license_normalized_comparison(self):
        """Test: License comparison handles different formats"""
        content = "Licensed plumber # TX 12345"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
        assert result['verification_score'] == 100
    
    def test_insurance_match(self):
        """Test: Insurance amount matches source"""
        content = "$2,000,000 insurance coverage"
        customer_profile = {'insurance_amount': '2000000'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
        assert result['verification_score'] == 100
    
    def test_insurance_mismatch(self):
        """Test: Insurance amount doesn't match source"""
        content = "$5,000,000 insurance coverage"
        customer_profile = {'insurance_amount': '1000000'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == False
        assert result['verification_score'] < 100
    
    def test_multiple_facts_partial_match(self):
        """Test: Multiple facts with some matching, some not"""
        content = "Licensed plumber #TX-12345 with $2,000,000 insurance coverage"
        customer_profile = {
            'license': 'TX-12345',  # Matches
            'insurance_amount': '1000000'  # Doesn't match
        }
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == False
        assert 0 < result['verification_score'] < 100
        assert len(result['failed_verifications']) == 1
        assert result['verification_results'][0]['verified'] == True  # License
        assert result['verification_results'][1]['verified'] == False  # Insurance
    
    def test_no_source_data(self):
        """Test: Content has facts but no source data to verify against"""
        content = "Licensed plumber #TX-12345"
        customer_profile = {}  # No license data
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == False
        assert 'Source data not available' in result['failed_verifications'][0]['reason']
    
    def test_non_ymyl_industry(self):
        """Test: Non-YMYL industry skips verification"""
        content = "Best blog posts about travel"
        customer_profile = {}
        
        result = self.checker.verify_content(content, customer_profile, 'blogging')
        
        assert result['is_ymyl'] == False
        assert result['verification_score'] == 100
        assert result['all_verified'] == True
    
    def test_ymyl_industry_no_critical_facts(self):
        """Test: YMYL industry but no critical facts found"""
        content = "We provide great plumbing service in Dallas"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['is_ymyl'] == True
        assert result['verification_score'] == 100
        assert result['all_verified'] == True
        assert 'No critical facts found' in result.get('note', '')
    
    def test_years_experience_match(self):
        """Test: Years of experience matches source"""
        content = "We have 15 years of experience"
        customer_profile = {'years_in_business': '15'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
    
    def test_years_experience_tolerance(self):
        """Test: Years of experience within tolerance"""
        content = "We have 20 years of experience"
        customer_profile = {'years_in_business': '19'}  # Within 10% tolerance
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
    
    def test_phone_number_extraction(self):
        """Test: Phone number extraction and verification"""
        content = "Call us at (214) 555-0100"
        customer_profile = {'phone': '(214) 555-0100'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
    
    def test_multiple_industries(self):
        """Test: Different YMYL industries"""
        industries = ['plumbing', 'electrical', 'legal', 'medical', 'finance']
        
        for industry in industries:
            assert industry in self.checker.YMYL_INDUSTRIES
    
    def test_severity_weighting(self):
        """Test: Critical facts weighted higher than low-severity"""
        content = """
        Licensed plumber #TX-99999
        20 years of experience
        """
        customer_profile = {
            'license': 'TX-12345',  # Critical - doesn't match
            'years_in_business': '20'  # Medium - matches
        }
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        # Score should be heavily penalized due to critical fact mismatch
        assert result['verification_score'] < 50
    
    def test_batch_verify(self):
        """Test: Batch verification of multiple items"""
        items = [
            {'id': '1', 'content': 'Licensed plumber #TX-12345'},
            {'id': '2', 'content': 'Licensed plumber #TX-99999'}
        ]
        
        customer_profiles = {
            '1': {'license': 'TX-12345'},
            '2': {'license': 'TX-12345'}
        }
        
        industry_map = {
            '1': 'plumbing',
            '2': 'plumbing'
        }
        
        results = self.checker.batch_verify(items, customer_profiles, industry_map)
        
        assert len(results) == 2
        assert results[0]['all_verified'] == True
        assert results[1]['all_verified'] == False
    
    def test_case_insensitive_matching(self):
        """Test: Verification is case-insensitive"""
        content = "Licensed plumber #tx-12345"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True
    
    def test_html_content(self):
        """Test: Can extract facts from HTML content"""
        content = "<h2>Licensed Plumber</h2><p>License #TX-12345</p>"
        customer_profile = {'license': 'TX-12345'}
        
        result = self.checker.verify_content(content, customer_profile, 'plumbing')
        
        assert result['all_verified'] == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
