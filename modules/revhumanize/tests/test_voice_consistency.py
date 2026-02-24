"""
Tests for Voice Consistency Checker
"""
import pytest
from app.validators.voice_checker import VoiceConsistencyChecker


class TestVoiceConsistencyChecker:
    """Test suite for voice consistency validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.checker = VoiceConsistencyChecker()
    
    def test_partner_voice_clean(self):
        """Test: Partner voice with clean, directive content"""
        content = "Contact us today for emergency plumbing service. Call now at (214) 555-0100."
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == True
        assert result['consistency_score'] >= 80
        assert result['target_voice'] == 'partner'
        assert len(result['violations']) == 0
    
    def test_partner_voice_tentative_language(self):
        """Test: Partner voice with tentative language (should fail)"""
        content = "Perhaps you might want to consider calling us for plumbing service."
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == False
        assert result['consistency_score'] < 80
        assert len(result['violations']) > 0
        assert result['violations'][0]['pattern_type'] == 'tentative_language'
    
    def test_partner_voice_empathetic_peer(self):
        """Test: Partner voice with empathetic peer language (should fail)"""
        content = "I understand how frustrating it can be when your pipes burst. We're here to help."
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == False
        assert any(v['pattern_type'] == 'empathetic_peer' for v in result['violations'])
    
    def test_partner_voice_academic_professor(self):
        """Test: Partner voice with academic language (should fail)"""
        content = "One might consider that plumbing emergencies require immediate attention. It is worth noting the importance of professional service."
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == False
        assert any(v['pattern_type'] == 'academic_professor' for v in result['violations'])
    
    def test_peer_voice_conversational(self):
        """Test: Peer voice with conversational tone (should pass)"""
        content = "I totally get it - dealing with a plumbing emergency is super stressful. Let me help you figure this out."
        
        result = self.checker.check_voice_consistency(content, 'peer')
        
        assert result['passed'] == True
        assert result['target_voice'] == 'peer'
    
    def test_peer_voice_sales_language(self):
        """Test: Peer voice with sales pressure (should fail)"""
        content = "Limited time offer! Don't miss out on our exclusive deal. Act now before it's too late!"
        
        result = self.checker.check_voice_consistency(content, 'peer')
        
        assert result['passed'] == False
        assert any(v['pattern_type'] == 'sales_language' for v in result['violations'])
    
    def test_professor_voice_educational(self):
        """Test: Professor voice with educational content (should pass)"""
        content = "Plumbing systems consist of interconnected pipes and fixtures. Understanding the fundamentals of water pressure is essential for proper maintenance."
        
        result = self.checker.check_voice_consistency(content, 'professor')
        
        # Should pass as it doesn't contain forbidden patterns
        assert result['passed'] == True
        assert result['target_voice'] == 'professor'
    
    def test_professor_voice_sales_pressure(self):
        """Test: Professor voice with sales pressure (should fail)"""
        content = "Buy now! Only 3 slots remaining for our plumbing certification course!"
        
        result = self.checker.check_voice_consistency(content, 'professor')
        
        assert result['passed'] == False
        assert any(v['pattern_type'] == 'sales_pressure' for v in result['violations'])
    
    def test_mixed_content(self):
        """Test: Content with multiple violations"""
        content = """
        Perhaps you might want to consider our plumbing services.
        I understand how frustrating it can be.
        One might argue that professional help is essential.
        """
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == False
        assert len(result['violations']) >= 3  # Multiple violations detected
    
    def test_html_content(self):
        """Test: Content with HTML tags (should strip tags)"""
        content = "<h2>Contact us today</h2><p>Call now for emergency service.</p>"
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['passed'] == True
        assert result['total_sentences'] > 0
    
    def test_empty_content(self):
        """Test: Empty content"""
        content = ""
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert result['consistency_score'] == 100
        assert result['total_sentences'] == 0
    
    def test_invalid_voice(self):
        """Test: Invalid voice parameter"""
        content = "Test content"
        
        with pytest.raises(ValueError):
            self.checker.check_voice_consistency(content, 'invalid_voice')
    
    def test_batch_check(self):
        """Test: Batch checking multiple items"""
        items = [
            {'id': '1', 'content': 'Contact us now for service.'},
            {'id': '2', 'content': 'Perhaps you might consider calling us.'}
        ]
        
        results = self.checker.batch_check(items, 'partner')
        
        assert len(results) == 2
        assert results[0]['passed'] == True
        assert results[1]['passed'] == False
        assert results[0]['content_id'] == '1'
        assert results[1]['content_id'] == '2'
    
    def test_violation_suggestions(self):
        """Test: Violations include fix suggestions"""
        content = "Perhaps you might want to consider our services."
        
        result = self.checker.check_voice_consistency(content, 'partner')
        
        assert len(result['violations']) > 0
        assert 'suggestion' in result['violations'][0]
        assert result['violations'][0]['suggestion'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
