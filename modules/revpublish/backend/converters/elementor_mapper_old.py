"""
Updated Elementor Mapper with Config-Driven Layout Generation
RevPublish v2.1 - Pure JSON Configuration
"""

import json
import uuid
from typing import Dict, List, Any
from pathlib import Path

# Import the config-driven layout system
from .page_layouts import layouts


class ElementorMapper:
    """Maps CSV data to Elementor JSON using Config-Driven Section Registry"""
    
    def __init__(self):
        self.layouts = layouts
    
    def map_to_elementor(self, config: Dict) -> Dict:
        """
        Main entry point - generates complete Elementor page
        
        Args:
            config: {
                'page_type_id': 'service_page',
                'color_scheme': 'professional',
                'animation_style': 'subtle',
                'field_data': {...}  # CSV row
            }
            
        Returns:
            Complete Elementor JSON structure
        """
        page_type_id = config.get('page_type_id', 'service_page')
        field_data = config.get('field_data', {})
        color_scheme = config.get('color_scheme', 'professional')
        animation_style = config.get('animation_style', 'subtle')
        
        # Use config-driven layout generation (generic, works for ALL page types)
        sections = self.layouts.generate_layout(
            page_type_id, 
            field_data, 
            color_scheme, 
            animation_style
        )
        
        # Wrap in Elementor structure
        return self._build_elementor_json(sections, field_data)
    
    def _build_elementor_json(self, sections: List[Dict], field_data: Dict) -> Dict:
        """Wrap sections in complete Elementor JSON structure"""
        
        return {
            'version': '0.4',
            'title': field_data.get('title') or field_data.get('business_name', 'Page'),
            'type': 'page',
            'content': sections,
            'page_settings': {
                'post_status': 'draft',
                'template': 'elementor_canvas'
            }
        }


# Singleton instance for backwards compatibility
elementor_mapper = ElementorMapper()
