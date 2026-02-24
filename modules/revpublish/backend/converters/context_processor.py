"""
Context Processing for RevPublish
Transforms raw CSV data into structured context for templates
"""

from typing import Dict, List, Any


class ContextProcessor:
    """Prepares context from CSV field_data for template rendering"""
    
    DELIMITER = '|||'  # Triple pipe to avoid conflicts
    
    def prepare_context(self, field_data: Dict, color_scheme: str = 'professional', 
                       animation_style: str = 'subtle') -> Dict:
        """
        Transform raw CSV data into rich context
        
        Args:
            field_data: Raw CSV row as dictionary
            color_scheme: Color scheme name
            animation_style: Animation style name
            
        Returns:
            Context dictionary with processed data
        """
        context = {}
        
        # Color scheme mapping
        colors = self._get_colors(color_scheme)
        context.update(colors)
        
        # Basic field mappings
        context['business_name'] = field_data.get('business_name', 'Business')
        context['city'] = field_data.get('city', '')
        context['state'] = field_data.get('state', '')
        context['phone'] = field_data.get('phone', '')
        context['email'] = field_data.get('email', '')
        context['niche'] = field_data.get('niche', 'Service')
        
        # Computed fields
        context['h1_text'] = f"{context['business_name']} - {context['niche']} in {context['city']}"
        context['subheading_text'] = f"Professional {context['niche']} serving {field_data.get('service_area', context['city'])}"
        context['map_address'] = f"{field_data.get('address', '')}, {context['city']}, {context['state']}"
        
        # CTA fields
        context['cta_text'] = f"Call {context['phone']}"
        context['cta_url'] = f"tel:{context['phone']}"
        context['cta_heading'] = 'Ready to Get Started?'
        context['cta_button_text'] = f"Call Now: {context['phone']}"
        context['cta_button_url'] = f"tel:{context['phone']}"
        
        # Process complex fields
        if field_data.get('hero_slider_images'):
            context['hero_slides'] = self._format_image_list(
                field_data.get('hero_slider_images')
            )
        
        if field_data.get('testimonial_names'):
            context['testimonial_slides'] = self._format_testimonials(field_data)
            context['testimonial_heading'] = 'What Our Customers Say'
        
        if field_data.get('certification_logos'):
            context['trust_logos'] = self._format_image_list(
                field_data.get('certification_logos')
            )
            context['trust_heading'] = 'Certified & Trusted'
        
        if field_data.get('services_offered'):
            context['services_items'] = self._format_icon_list(
                field_data.get('services_offered')
            )
            context['services_heading'] = 'Our Services'
        
        if field_data.get('neighborhood_coverage'):
            context['neighborhoods_items'] = self._format_icon_list(
                field_data.get('neighborhood_coverage')
            )
            context['neighborhoods_heading'] = f"Neighborhoods We Serve in {context['city']}"
        
        # Map section
        context['map_heading'] = 'Find Us'
        
        # About section
        context['about_heading'] = f"About {context['business_name']}"
        context['about_text'] = field_data.get('about_business', f"Professional {context['niche']} services in {context['city']}")
        
        # Services grid
        context['services_grid_heading'] = 'Our Services'
        if field_data.get('services_offered'):
            context['services_grid_items'] = self._format_services_grid(
                field_data.get('services_offered')
            )
        
        return context
    
    def _get_colors(self, scheme: str) -> Dict:
        """Get color palette for scheme"""
        schemes = {
            'professional': {
                'primary_color': '#1e40af',
                'secondary_color': '#64748b',
                'accent_color': '#22c55e',
                'hero_bg_color': '#f8fafc',
                'cta_bg_color': '#1e40af'
            },
            'urgent': {
                'primary_color': '#dc2626',
                'secondary_color': '#f97316',
                'accent_color': '#fbbf24',
                'hero_bg_color': '#fef2f2',
                'cta_bg_color': '#dc2626'
            }
        }
        return schemes.get(scheme, schemes['professional'])
    
    def _format_testimonials(self, field_data: Dict) -> List[Dict]:
        """Convert parallel pipe strings to testimonial slides"""
        names = str(field_data.get('testimonial_names', '')).split(self.DELIMITER)
        texts = str(field_data.get('testimonial_texts', '')).split(self.DELIMITER)
        ratings = str(field_data.get('testimonial_ratings', '5')).split(self.DELIMITER)
        
        slides = []
        for i in range(len(names)):
            if names[i].strip():
                slides.append({
                    'testimonial_name': names[i].strip(),
                    'testimonial_content': texts[i].strip() if i < len(texts) else '',
                    'testimonial_rating': ratings[i].strip() if i < len(ratings) else '5',
                    'testimonial_image': {'url': ''}  # Placeholder
                })
        
        return slides
    
    def _format_image_list(self, pipe_string: str) -> List[Dict]:
        """Convert pipe-delimited images to Elementor format"""
        images = pipe_string.split(self.DELIMITER)
        return [{'url': img.strip(), 'id': ''} for img in images if img.strip()]
    
    def _format_icon_list(self, pipe_string: str) -> List[Dict]:
        """Convert pipe-delimited text to icon list items"""
        items = pipe_string.split(self.DELIMITER)
        return [{'text': item.strip()} for item in items if item.strip()]
    
    def _format_services_grid(self, pipe_string: str) -> List[Dict]:
        """Convert services to icon box grid items"""
        services = pipe_string.split(self.DELIMITER)
        return [{
            'title': service.strip(),
            'description': f"Professional {service.strip()} services",
            'icon': {'value': 'fas fa-check-circle', 'library': 'fa-solid'}
        } for service in services if service.strip()]


# Singleton instance
processor = ContextProcessor()
