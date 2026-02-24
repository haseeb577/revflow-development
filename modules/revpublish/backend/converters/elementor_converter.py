"""
HTML to Elementor JSON Converter
Converts HTML content to Elementor-compatible JSON structure
"""

from bs4 import BeautifulSoup
from typing import Dict, List
import json

class ElementorConverter:
    """Converts HTML to Elementor JSON format"""
    
    def __init__(self):
        self.element_id_counter = 0
    
    def convert_html_to_elementor(self, html_content: str) -> Dict:
        """
        Convert HTML string to Elementor JSON structure
        
        Args:
            html_content: HTML string to convert
        
        Returns:
            Dict containing Elementor JSON structure
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Create root container
        elementor_data = {
            'version': '0.4',
            'elements': []
        }
        
        # Create section container
        section = self._create_section()
        column = self._create_column()
        
        # Parse HTML elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'img']):
            elementor_element = self._convert_element(element)
            if elementor_element:
                column['elements'].append(elementor_element)
        
        # Build structure
        section['elements'].append(column)
        elementor_data['elements'].append(section)
        
        return elementor_data
    
    def _create_section(self, settings: Dict = None) -> Dict:
        """Create Elementor section container"""
        self.element_id_counter += 1
        return {
            'id': f'section_{self.element_id_counter}',
            'elType': 'section',
            'settings': settings or {},
            'elements': []
        }
    
    def _create_column(self, settings: Dict = None) -> Dict:
        """Create Elementor column container"""
        self.element_id_counter += 1
        return {
            'id': f'column_{self.element_id_counter}',
            'elType': 'column',
            'settings': settings or {'_column_size': 100},
            'elements': []
        }
    
    def _convert_element(self, element) -> Dict:
        """Convert single HTML element to Elementor widget"""
        self.element_id_counter += 1
        
        tag = element.name
        content = element.get_text()
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return {
                'id': f'heading_{self.element_id_counter}',
                'elType': 'widget',
                'widgetType': 'heading',
                'settings': {
                    'title': content,
                    'header_size': tag
                }
            }
        
        elif tag == 'p':
            return {
                'id': f'text_{self.element_id_counter}',
                'elType': 'widget',
                'widgetType': 'text-editor',
                'settings': {
                    'editor': content
                }
            }
        
        elif tag == 'img':
            return {
                'id': f'image_{self.element_id_counter}',
                'elType': 'widget',
                'widgetType': 'image',
                'settings': {
                    'image': {'url': element.get('src', '')}
                }
            }
        
        return None
