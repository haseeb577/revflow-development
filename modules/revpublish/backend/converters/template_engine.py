"""
RevPublish Template Engine
Converts structured data + templates into Elementor-ready content
"""

import json
import re
import copy
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db_connection


class TemplateEngine:
    """Processes page types, fields, and templates"""

    def get_page_types(self) -> List[Dict]:
        """Get all available page types"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT type_id, type_name, description
                FROM revpublish_page_types
                ORDER BY type_name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_page_fields(self, page_type_id: str) -> List[Dict]:
        """Get fields for a specific page type"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_name, field_label, field_type, is_required,
                       placeholder, description
                FROM revpublish_page_fields
                WHERE page_type_id = %s
                ORDER BY field_order
            """, (page_type_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_template(self, page_type_id: str, template_name: Optional[str] = None) -> Dict:
        """Get Elementor template for page type"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if template_name:
                cursor.execute("""
                    SELECT elementor_json
                    FROM revpublish_templates
                    WHERE page_type_id = %s AND template_name = %s
                """, (page_type_id, template_name))
            else:
                cursor.execute("""
                    SELECT elementor_json
                    FROM revpublish_templates
                    WHERE page_type_id = %s AND is_default = true
                """, (page_type_id,))

            row = cursor.fetchone()
            if row:
                return row['elementor_json']
            return None

    def render_template(self, page_type_id: str, data: Dict, template_name: Optional[str] = None) -> Dict:
        """
        Render a template with provided data

        Args:
            page_type_id: Type of page (service_page, location_page, blog_post)
            data: Dictionary of field values
            template_name: Optional specific template name

        Returns:
            Rendered Elementor JSON structure
        """
        template = self.get_template(page_type_id, template_name)
        if not template:
            raise ValueError(f"No template found for page type: {page_type_id}")

        # Deep copy template to avoid modifying original
        rendered = copy.deepcopy(template)

        # Process list fields into Elementor format
        processed_data = self._process_data(data)

        # Replace placeholders in template
        rendered = self._replace_placeholders(rendered, processed_data)

        return rendered

    def _process_data(self, data: Dict) -> Dict:
        """Process data fields, converting lists etc."""
        processed = dict(data)

        # Convert pipe-separated lists to Elementor icon-list format
        for key, value in data.items():
            if isinstance(value, str) and '|' in value:
                items = [item.strip() for item in value.split('|')]
                # Create icon list format
                processed[f'{key}_as_list'] = [
                    {'text': item, 'icon': {'value': 'fas fa-check', 'library': 'fa-solid'}}
                    for item in items
                ]
            elif isinstance(value, list):
                processed[f'{key}_as_list'] = [
                    {'text': item, 'icon': {'value': 'fas fa-check', 'library': 'fa-solid'}}
                    for item in value
                ]

        return processed

    def _replace_placeholders(self, obj, data: Dict):
        """Recursively replace {{placeholders}} in template"""
        if isinstance(obj, dict):
            return {k: self._replace_placeholders(v, data) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_placeholders(item, data) for item in obj]
        elif isinstance(obj, str):
            # Replace {{field_name}} placeholders
            pattern = r'\{\{(\w+)\}\}'

            def replace_match(match):
                field_name = match.group(1)
                value = data.get(field_name, match.group(0))
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                return str(value) if value else ''

            return re.sub(pattern, replace_match, obj)
        else:
            return obj

    def generate_page_content(self, page_type_id: str, data: Dict) -> Dict:
        """
        Generate complete page content from structured data

        Returns dict with:
        - title: Page/post title
        - content: HTML content (fallback)
        - elementor_data: Elementor JSON structure
        - meta: SEO meta fields
        """
        # Get template and render
        elementor_data = self.render_template(page_type_id, data)

        # Generate title based on page type
        if page_type_id == 'service_page':
            title = data.get('hero_headline') or data.get('service_name', 'Service Page')
        elif page_type_id == 'location_page':
            city = data.get('city', '')
            service = data.get('service_name', '')
            title = f"{city} {service}".strip() or 'Location Page'
        elif page_type_id == 'blog_post':
            title = data.get('title', 'Blog Post')
        else:
            title = data.get('title') or data.get('hero_headline', 'Page')

        # Generate HTML fallback content
        html_content = self._generate_html_fallback(page_type_id, data)

        # Generate meta description
        meta_description = data.get('excerpt') or data.get('hero_subheadline', '')[:160]

        return {
            'title': title,
            'content': html_content,
            'elementor_data': elementor_data,
            'excerpt': data.get('excerpt', meta_description),
            'meta': {
                'description': meta_description,
                'keywords': self._generate_keywords(page_type_id, data)
            }
        }

    def _generate_html_fallback(self, page_type_id: str, data: Dict) -> str:
        """Generate basic HTML content as fallback"""
        html_parts = []

        if page_type_id == 'service_page':
            if data.get('hero_headline'):
                html_parts.append(f"<h1>{data['hero_headline']}</h1>")
            if data.get('hero_subheadline'):
                html_parts.append(f"<p><em>{data['hero_subheadline']}</em></p>")
            if data.get('service_description'):
                html_parts.append(data['service_description'])
            if data.get('benefits'):
                benefits = data['benefits'].split('|') if isinstance(data['benefits'], str) else data['benefits']
                html_parts.append("<h2>Why Choose Us</h2><ul>")
                html_parts.extend(f"<li>{b.strip()}</li>" for b in benefits)
                html_parts.append("</ul>")

        elif page_type_id == 'location_page':
            city = data.get('city', '')
            service = data.get('service_name', '')
            html_parts.append(f"<h1>{city} {service}</h1>")
            if data.get('local_description'):
                html_parts.append(data['local_description'])
            if data.get('service_areas'):
                areas = data['service_areas'].split('|') if isinstance(data['service_areas'], str) else data['service_areas']
                html_parts.append(f"<h2>Areas We Serve in {city}</h2><ul>")
                html_parts.extend(f"<li>{a.strip()}</li>" for a in areas)
                html_parts.append("</ul>")

        elif page_type_id == 'blog_post':
            if data.get('content'):
                html_parts.append(data['content'])

        return '\n'.join(html_parts)

    def _generate_keywords(self, page_type_id: str, data: Dict) -> str:
        """Generate SEO keywords from data"""
        keywords = []

        if page_type_id == 'service_page':
            if data.get('service_name'):
                keywords.append(data['service_name'])
            if data.get('benefits'):
                benefits = data['benefits'].split('|') if isinstance(data['benefits'], str) else data['benefits']
                keywords.extend(b.strip() for b in benefits[:3])

        elif page_type_id == 'location_page':
            if data.get('city'):
                keywords.append(data['city'])
            if data.get('service_name'):
                keywords.append(data['service_name'])
            keywords.append(f"{data.get('city', '')} {data.get('service_name', '')}")

        return ', '.join(keywords)


# Singleton instance
template_engine = TemplateEngine()
