"""
Updated Elementor Mapper with Section Registry Integration
RevPublish v2.0 - Layout Intelligence Layer
"""

import json
import uuid
from typing import Dict, List, Any
from pathlib import Path

# Import the new modules
from .page_layouts import layouts


class ElementorMapper:
    """Maps CSV data to Elementor JSON using Section Registry"""
    
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
        
        # Route to appropriate layout function
        sections = self._generate_layout(
            page_type_id, 
            field_data, 
            color_scheme, 
            animation_style
        )
        
        # Wrap in Elementor structure
        return self._build_elementor_json(sections, field_data)
    
    def _generate_layout(self, page_type_id: str, field_data: Dict,
                        color_scheme: str, animation_style: str) -> List[Dict]:
        """Route to page-type-specific layout function"""
        
        layout_map = {
            'service_page': self.layouts.generate_service_page_layout,
            'location_page': self.layouts.generate_location_page_layout,
            'homepage': self.layouts.generate_homepage_layout
        }
        
        layout_function = layout_map.get(page_type_id)
        
        if not layout_function:
            raise ValueError(f"Unknown page_type_id: {page_type_id}")
        
        return layout_function(field_data, color_scheme, animation_style)
    
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
