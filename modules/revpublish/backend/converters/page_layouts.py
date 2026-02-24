"""
Page Layout Intelligence for RevPublish
Defines layout logic for each page type
"""

from typing import Dict, List
from .template_renderer import renderer
from .context_processor import processor


class PageLayouts:
    """Page-type-specific layout generation"""
    
    def generate_service_page_layout(self, field_data: Dict, color_scheme: str, 
                                     animation_style: str) -> List[Dict]:
        """Generate Service Page layout"""
        context = processor.prepare_context(field_data, color_scheme, animation_style)
        sections = []
        
        # Hero section (always)
        sections.append(renderer.render_template('hero_standard', context))
        
        # Hero image carousel (conditional)
        if 'hero_slides' in context:
            sections.append(renderer.render_template('hero_image_carousel', context))
        
        # Services list (conditional)
        if 'services_items' in context:
            sections.append(renderer.render_template('services_list', context))
        
        # Testimonials (conditional)
        if 'testimonial_slides' in context:
            sections.append(renderer.render_template('testimonial_carousel', context))
        
        # Trust badges (conditional)
        if 'trust_logos' in context:
            sections.append(renderer.render_template('trust_badges', context))
        
        # Contact CTA (always)
        sections.append(renderer.render_template('contact_cta', context))
        
        return sections
    
    def generate_location_page_layout(self, field_data: Dict, color_scheme: str,
                                      animation_style: str) -> List[Dict]:
        """Generate Location Page layout"""
        context = processor.prepare_context(field_data, color_scheme, animation_style)
        
        # Override H1 for location pages (use location_name if available)
        location_name = field_data.get('location_name', context['city'])
        context['h1_text'] = f"{context['business_name']} in {location_name}"
        context['subheading_text'] = f"Professional {context['niche']} for {location_name} Residents"
        
        sections = []
        
        # Hero
        sections.append(renderer.render_template('hero_standard', context))
        
        # Map section (always for location pages)
        sections.append(renderer.render_template('map_section', context))
        
        # Neighborhoods (conditional)
        if 'neighborhoods_items' in context:
            sections.append(renderer.render_template('neighborhoods_list', context))
        
        # Services
        if 'services_items' in context:
            sections.append(renderer.render_template('services_list', context))
        
        # Testimonials
        if 'testimonial_slides' in context:
            sections.append(renderer.render_template('testimonial_carousel', context))
        
        # CTA
        sections.append(renderer.render_template('contact_cta', context))
        
        return sections
    
    def generate_homepage_layout(self, field_data: Dict, color_scheme: str,
                                 animation_style: str) -> List[Dict]:
        """Generate Homepage layout"""
        context = processor.prepare_context(field_data, color_scheme, animation_style)
        
        # Homepage uses hero_headline if available
        if field_data.get('hero_headline'):
            context['h1_text'] = field_data.get('hero_headline')
            context['subheading_text'] = field_data.get('hero_subheadline', context['subheading_text'])
        
        # Custom CTAs if provided
        if field_data.get('cta_primary'):
            context['cta_text'] = field_data.get('cta_primary')
        
        sections = []
        
        # Hero
        sections.append(renderer.render_template('hero_standard', context))
        
        # Hero carousel
        if 'hero_slides' in context:
            sections.append(renderer.render_template('hero_image_carousel', context))
        
        # Services grid (homepage uses grid not list)
        if 'services_grid_items' in context:
            sections.append(renderer.render_template('services_grid', context))
        
        # About section
        sections.append(renderer.render_template('about_content', context))
        
        # Testimonials
        if 'testimonial_slides' in context:
            sections.append(renderer.render_template('testimonial_carousel', context))
        
        # Trust badges
        if 'trust_logos' in context:
            sections.append(renderer.render_template('trust_badges', context))
        
        # CTA
        sections.append(renderer.render_template('contact_cta', context))
        
        return sections


# Singleton instance
layouts = PageLayouts()
