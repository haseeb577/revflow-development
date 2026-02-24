# RevPublish Implementation Plan
## Google Docs Template → Elementor JSON Conversion

## 📋 Current State Analysis

### What Exists:
1. ✅ Basic CSV import endpoint (`/api/import`)
2. ✅ Merge field replacement (`merge_template_fields()`)
3. ✅ Simple Elementor JSON builder (`build_elementor_json()`)
4. ✅ Google Docs client for fetching public docs (`GoogleDocsClient`)
5. ✅ Basic HTML-to-Elementor converter (`ElementorConverter`)

### What's Missing:
1. ❌ Google Doc URL processing in CSV import
2. ❌ Sophisticated HTML-to-Elementor conversion (button widgets, icon-lists, etc.)
3. ❌ Section-based parsing (Hero, Intro, Services, Contact sections)
4. ❌ Phone number detection and button widget conversion
5. ❌ List (ul/ol) to icon-list widget conversion
6. ❌ Background/gradient settings for sections

---

## 🎯 Implementation Requirements

### Phase 1: Enhanced HTML-to-Elementor Converter

**File:** `modules/revpublish/backend/converters/elementor_converter.py`

**Required Features:**
1. **Section Detection**
   - Detect sections by headings (H1 = Hero, H2 = Content sections)
   - Create separate Elementor sections for each major section
   - Support section settings (backgrounds, gradients, padding)

2. **Widget Mappings:**
   - `h1-h6` → `heading` widget with proper header_size
   - `p` → `text-editor` widget with HTML content
   - `ul/ol` → `icon-list` widget with icon_list array
   - Phone numbers in text → `button` widget with `tel:` link
   - `img` → `image` widget
   - Email addresses → clickable links in text-editor

3. **Smart Content Detection:**
   - Detect phone numbers: `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`
   - Detect email addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
   - Convert phone numbers to button widgets
   - Preserve email as clickable links

4. **Section Settings:**
   - Hero sections: gradient backgrounds
   - Contact sections: different background colors
   - Padding and spacing controls

### Phase 2: Google Docs Integration in CSV Import

**File:** `modules/revpublish/backend/main.py` (bulk_import_csv_template function)

**Required Changes:**
1. **Check for Google Doc URL:**
   - Check CSV for `page_content_doc_url` column
   - If present, fetch Google Doc content
   - If not present, use uploaded template file (existing behavior)

2. **Template Priority:**
   - Priority 1: `page_content_doc_url` from CSV row
   - Priority 2: Uploaded template file
   - Priority 3: Fallback to basic Elementor structure

3. **Merge Process:**
   - Fetch Google Doc HTML content
   - Replace merge fields in HTML: `[BUSINESS_NAME]`, `[CITY]`, etc.
   - Convert merged HTML to Elementor JSON
   - Deploy to WordPress

### Phase 3: Enhanced Merge Field Support

**File:** `modules/revpublish/backend/main.py` (merge_template_fields function)

**Enhancements:**
1. Support section markers: `[HERO_SECTION]`, `[CONTACT_SECTION]`
2. Support conditional content: `[IF emergency_available=yes]...[/IF]`
3. Support phone formatting: `[PHONE]` → button widget automatically
4. Support list generation from CSV data

---

## 🔧 Detailed Implementation Steps

### Step 1: Enhance ElementorConverter Class

```python
class EnhancedElementorConverter:
    """Enhanced HTML to Elementor JSON converter"""
    
    def convert_html_to_elementor(self, html_content: str, row_data: Dict = None) -> List[Dict]:
        """
        Convert HTML to Elementor JSON with sophisticated widget mapping
        
        Features:
        - Section detection (Hero, Content, Contact)
        - Phone number → button widget
        - Lists → icon-list widget
        - Headings → heading widget
        - Paragraphs → text-editor widget
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = []
        current_section = None
        
        # Parse body content
        body = soup.find('body') or soup
        
        for element in body.children:
            # Detect section breaks (H1 or H2)
            if element.name in ['h1', 'h2']:
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                current_section = self._create_section_from_heading(element)
            
            # Add elements to current section
            if current_section:
                widget = self._convert_to_widget(element, row_data)
                if widget:
                    current_section['elements'][0]['elements'].append(widget)
        
        # Add last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _convert_to_widget(self, element, row_data: Dict = None) -> Dict:
        """Convert HTML element to Elementor widget"""
        # Phone number detection and button conversion
        # List to icon-list conversion
        # Heading to heading widget
        # etc.
```

### Step 2: Update CSV Import Endpoint

```python
@app.post("/api/import")
async def bulk_import_csv_template(...):
    # ... existing code ...
    
    for index, row in df.iterrows():
        row_dict = row.to_dict()
        
        # NEW: Check for Google Doc URL
        doc_url = row_dict.get('page_content_doc_url', '').strip()
        
        if doc_url:
            # Fetch Google Doc content
            from integrations.google_integrations import GoogleDocsClient
            google_docs = GoogleDocsClient()
            doc_content = google_docs.extract_from_url(doc_url)
            template_text = doc_content['content_html']
        elif template_file:
            # Use uploaded template
            template_text = template_content.decode('utf-8')
        else:
            # Fallback to basic structure
            template_text = None
        
        # Merge fields in template
        if template_text:
            merged_html = merge_template_fields(template_text, row_dict)
            
            # Convert HTML to Elementor JSON
            from converters.elementor_converter import EnhancedElementorConverter
            converter = EnhancedElementorConverter()
            elementor_data = converter.convert_html_to_elementor(merged_html, row_dict)
        else:
            # Fallback to basic Elementor structure
            elementor_data = build_elementor_json(row_dict)
        
        # Deploy to WordPress
        # ... existing deployment code ...
```

### Step 3: Phone Number Detection & Button Widget

```python
def _detect_phone_numbers(self, text: str) -> List[Dict]:
    """Detect phone numbers in text and convert to button widgets"""
    import re
    
    phone_pattern = r'\b(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    matches = re.finditer(phone_pattern, text)
    
    buttons = []
    for match in matches:
        phone = re.sub(r'[^\d]', '', match.group(0))
        if len(phone) == 10 or (len(phone) == 11 and phone.startswith('1')):
            if len(phone) == 11:
                phone = phone[1:]  # Remove leading 1
            formatted = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
            buttons.append({
                'elType': 'widget',
                'widgetType': 'button',
                'settings': {
                    'text': f'📞 {formatted}',
                    'link': {'url': f'tel:{phone}'},
                    'align': 'center'
                }
            })
    
    return buttons
```

### Step 4: List to Icon-List Conversion

```python
def _convert_list_to_icon_list(self, list_element) -> Dict:
    """Convert ul/ol to icon-list widget"""
    items = []
    for li in list_element.find_all('li', recursive=False):
        text = li.get_text(strip=True)
        # Remove checkmarks/bullets if present
        text = re.sub(r'^[✓✔•\-\*]\s*', '', text)
        items.append({
            'text': text,
            'icon': 'fa fa-check'  # Default icon
        })
    
    return {
        'elType': 'widget',
        'widgetType': 'icon-list',
        'settings': {
            'icon_list': items
        }
    }
```

---

## 📝 Testing Checklist

- [ ] Google Doc URL in CSV is fetched correctly
- [ ] Merge fields are replaced in Google Doc HTML
- [ ] HTML is converted to Elementor JSON correctly
- [ ] Phone numbers become button widgets
- [ ] Lists become icon-list widgets
- [ ] Headings become heading widgets
- [ ] Sections are created properly
- [ ] Backgrounds/gradients work
- [ ] Deployment to WordPress succeeds
- [ ] Elementor pages render correctly

---

## 🚀 Implementation Order

1. **First:** Enhance `ElementorConverter` class with all widget mappings
2. **Second:** Add Google Doc URL processing to CSV import
3. **Third:** Test with sample Google Doc template
4. **Fourth:** Refine and optimize
5. **Fifth:** Update documentation

---

## ⚠️ Important Notes

1. **Bridge Plugin:** Still assumed to be external WordPress plugin
2. **Elementor Version:** Using Elementor JSON format v0.4
3. **Widget Support:** Only confirmed working widgets should be used
4. **Error Handling:** Must handle Google Doc fetch failures gracefully
5. **Performance:** Consider caching Google Doc content for bulk imports

