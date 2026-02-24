# RevPublish Complete Implementation Plan
## CSV → Google Docs → WordPress/Elementor Flow

## 🎯 Understanding the Complete Flow

Based on the documentation, there are **TWO deployment modes**:

### Mode 1: HTML → Bridge Plugin (Recommended per new docs)
1. Fetch Google Doc content
2. Merge fields with CSV data
3. Send HTML to WordPress REST API
4. **Bridge Plugin** (WordPress plugin) converts HTML → Elementor JSON
5. Result: Elementor page

### Mode 2: Direct Elementor JSON (Current implementation)
1. Build Elementor JSON from CSV data
2. Send Elementor JSON directly to WordPress
3. No Bridge Plugin needed
4. Result: Elementor page

**Decision:** Support **BOTH modes** but prioritize **Mode 1** (HTML → Bridge Plugin) as it's simpler and matches the documentation.

---

## 📋 Implementation Requirements

### Phase 1: Google Docs Integration in CSV Import

**File:** `modules/revpublish/backend/main.py` (`bulk_import_csv_template` function)

**Changes Needed:**

1. **Check for `page_content_doc_url` column in CSV**
   ```python
   if 'page_content_doc_url' in df.columns:
       # Process Google Doc URLs
   ```

2. **Fetch Google Doc content for each row**
   ```python
   doc_url = row_dict.get('page_content_doc_url', '').strip()
   if doc_url:
       from integrations.google_integrations import GoogleDocsClient
       google_docs = GoogleDocsClient()
       doc_content = google_docs.extract_from_url(doc_url)
       template_html = doc_content['content_html']
   ```

3. **Merge fields in Google Doc HTML**
   ```python
   merged_html = merge_template_fields(template_html, row_dict)
   ```

4. **Send HTML to WordPress (Mode 1) OR convert to Elementor JSON (Mode 2)**
   ```python
   # Mode 1: HTML → Bridge Plugin
   content = merged_html
   use_elementor = True  # Bridge Plugin will convert
   
   # Mode 2: Direct Elementor JSON (existing)
   # elementor_data = convert_html_to_elementor(merged_html)
   ```

---

### Phase 2: Enhanced Merge Field Support

**File:** `modules/revpublish/backend/main.py` (`merge_template_fields` function)

**Current Support:**
- ✅ Basic merge: `[FIELD_NAME]` → CSV value
- ✅ Conditional: `[IF field=value]content[/IF]`
- ✅ Markdown: `# Heading`, `**bold**`

**Enhancements Needed:**
1. **Phone number formatting**
   - `[PHONE]` → Formatted as "214-555-0100"
   - Auto-detect and format phone numbers

2. **Email link generation**
   - `[EMAIL]` → `<a href="mailto:email@example.com">email@example.com</a>`

3. **Address formatting**
   - `[ADDRESS]`, `[CITY]`, `[STATE]`, `[ZIP_CODE]` → Formatted address block

4. **List generation from pipe-delimited fields**
   - `services_offered` = "Service 1|||Service 2|||Service 3"
   - Convert to HTML `<ul><li>` list

---

### Phase 3: HTML Content Processing

**File:** `modules/revpublish/backend/main.py` (new function)

**Purpose:** Clean and prepare HTML for WordPress/Bridge Plugin

**Functions:**
1. **Clean Google Doc HTML**
   - Remove Google-specific classes/attributes
   - Preserve structure (headings, paragraphs, lists)
   - Clean up inline styles if needed

2. **Enhance HTML for Elementor**
   - Ensure proper heading hierarchy (h1, h2, h3)
   - Convert lists to proper `<ul>`/`<ol>` format
   - Preserve formatting (bold, italic, links)

3. **Phone number detection and enhancement**
   - Find phone numbers in text
   - Optionally convert to clickable `tel:` links
   - Format consistently

---

### Phase 4: Deployment Mode Selection

**File:** `modules/revpublish/backend/main.py` (`deploy_to_wordpress` function)

**Add parameter:**
```python
def deploy_to_wordpress(
    site_url: str,
    title: str,
    content: str,  # HTML content
    status: str = "draft",
    meta_data: Optional[Dict[str, Any]] = None,
    use_bridge_plugin: bool = True,  # NEW: Use Bridge Plugin or direct Elementor JSON
    use_elementor: bool = True
):
```

**Logic:**
```python
if use_bridge_plugin:
    # Mode 1: Send HTML, let Bridge Plugin convert
    payload = {
        'title': title,
        'content': content,  # HTML content
        'status': status
    }
    # Bridge Plugin will handle Elementor conversion
else:
    # Mode 2: Send Elementor JSON directly (existing code)
    payload = {
        'title': title,
        'content': '',
        'status': status,
        'meta': {
            '_elementor_data': json.dumps(elementor_json),
            '_elementor_edit_mode': 'builder'
        }
    }
```

---

## 🔧 Detailed Implementation Steps

### Step 1: Update CSV Import Endpoint

**Location:** `modules/revpublish/backend/main.py:499`

**Changes:**
```python
@app.post("/api/import")
async def bulk_import_csv_template(
    csv_file: UploadFile = File(...),
    template_file: UploadFile = File(None),
    enable_smart_corrections: bool = Form(True),
    use_llm_assistance: bool = Form(False),
    preview_mode: bool = Form(False),
    post_status: str = Form("draft"),
    use_bridge_plugin: bool = Form(True)  # NEW parameter
):
    # ... existing CSV parsing ...
    
    for index, row in df.iterrows():
        row_dict = row.to_dict()
        target_site = row_dict.get('site_url', '').strip()
        
        # NEW: Check for Google Doc URL
        doc_url = row_dict.get('page_content_doc_url', '').strip()
        template_html = None
        
        if doc_url:
            # Fetch Google Doc content
            try:
                from integrations.google_integrations import GoogleDocsClient
                google_docs = GoogleDocsClient()
                doc_content = google_docs.extract_from_url(doc_url)
                template_html = doc_content['content_html']
                print(f"✅ Fetched Google Doc: {doc_url}")
            except Exception as e:
                print(f"❌ Failed to fetch Google Doc {doc_url}: {e}")
                # Fall back to uploaded template or basic structure
                if template_file:
                    template_content = await template_file.read()
                    template_html = template_content.decode('utf-8')
        elif template_file:
            # Use uploaded template file
            template_content = await template_file.read()
            template_html = template_content.decode('utf-8')
        
        # Merge fields in template
        if template_html:
            merged_html = merge_template_fields(template_html, row_dict)
            page_content = merged_html
        else:
            # Fallback: Use basic HTML from CSV data
            page_content = build_elementor_page_content(row_dict)
        
        # Generate page title
        business_name = row_dict.get('business_name', '')
        niche = row_dict.get('niche', 'Services')
        city = row_dict.get('city', '')
        state = row_dict.get('state', '')
        page_title = f"{business_name} - {niche} in {city}, {state}".strip()
        
        # Deploy to WordPress
        if not preview_mode:
            success, error_msg, wp_post_id, wp_edit_url = deploy_to_wordpress(
                site_url=target_site,
                title=page_title,
                content=page_content,  # HTML content
                status=post_status,
                use_bridge_plugin=use_bridge_plugin,  # NEW
                use_elementor=True
            )
```

---

### Step 2: Enhance Merge Field Function

**Location:** `modules/revpublish/backend/main.py:132`

**Add phone formatting:**
```python
def merge_template_fields(template: str, row_data: Dict[str, Any]) -> str:
    merged = template
    
    # Format phone numbers
    if 'phone' in row_data and row_data['phone']:
        phone = str(row_data['phone'])
        # Normalize phone format
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            formatted_phone = f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        else:
            formatted_phone = phone
        row_data['phone'] = formatted_phone
    
    # Replace merge fields
    for field_name, field_value in row_data.items():
        field_placeholder = f"[{field_name.upper()}]"
        if pd.isna(field_value) or field_value is None:
            field_value = ""
        else:
            field_value = str(field_value)
        merged = merged.replace(field_placeholder, field_value)
    
    # Enhanced: Email link generation
    email_pattern = r'\[EMAIL\]'
    if 'email' in row_data and row_data['email']:
        email = str(row_data['email'])
        email_link = f'<a href="mailto:{email}">{email}</a>'
        merged = re.sub(email_pattern, email_link, merged, flags=re.IGNORECASE)
    
    # Enhanced: Phone link generation
    phone_pattern = r'\[PHONE_LINK\]'
    if 'phone' in row_data and row_data['phone']:
        phone = str(row_data['phone']).replace('-', '').replace(' ', '')
        phone_link = f'<a href="tel:{phone}">{row_data["phone"]}</a>'
        merged = re.sub(phone_pattern, phone_link, merged, flags=re.IGNORECASE)
    
    # Enhanced: List generation from pipe-delimited fields
    # [SERVICES_LIST] → <ul><li>Service 1</li><li>Service 2</li></ul>
    services_pattern = r'\[SERVICES_LIST\]'
    if 'services_offered' in row_data and row_data['services_offered']:
        services = str(row_data['services_offered']).split('|||')
        services_html = '<ul>' + ''.join([f'<li>{s.strip()}</li>' for s in services if s.strip()]) + '</ul>'
        merged = re.sub(services_pattern, services_html, merged, flags=re.IGNORECASE)
    
    # Existing conditional and markdown support
    # ... (keep existing code)
    
    return merged
```

---

### Step 3: Update Deployment Function

**Location:** `modules/revpublish/backend/main.py:383`

**Add Bridge Plugin mode:**
```python
def deploy_to_wordpress(
    site_url: str,
    title: str,
    content: str,  # HTML content
    status: str = "draft",
    meta_data: Optional[Dict[str, Any]] = None,
    use_bridge_plugin: bool = True,  # NEW
    use_elementor: bool = True
) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
    """
    Deploy content to WordPress site.
    
    Args:
        use_bridge_plugin: If True, send HTML and let Bridge Plugin convert to Elementor.
                          If False, send Elementor JSON directly.
    """
    try:
        creds = get_wordpress_credentials(site_url)
        if not creds:
            return False, f"No WordPress credentials found for {site_url}", None, None
        
        endpoint_type = 'pages' if use_elementor else 'posts'
        api_url = creds['api_url'].rstrip('/') + f'/{endpoint_type}'
        
        if use_bridge_plugin:
            # Mode 1: HTML → Bridge Plugin
            payload = {
                'title': title,
                'content': content,  # HTML content
                'status': status
            }
            # Bridge Plugin will detect and convert to Elementor
        else:
            # Mode 2: Direct Elementor JSON (existing)
            payload = {
                'title': title,
                'content': content,
                'status': status
            }
            
            if use_elementor and meta_data and 'elementor_data' in meta_data:
                elementor_json_string = json.dumps(meta_data['elementor_data'])
                payload['meta'] = {
                    '_elementor_data': elementor_json_string,
                    '_elementor_edit_mode': 'builder',
                    '_elementor_template_type': 'page'
                }
        
        # Make API request
        response = requests.post(
            api_url,
            json=payload,
            auth=(creds['username'], creds['password']),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # ... existing error handling ...
```

---

## 📝 Testing Checklist

### Google Docs Integration
- [ ] CSV with `page_content_doc_url` column is processed
- [ ] Google Doc is fetched successfully (public docs)
- [ ] Error handling for private/non-existent docs
- [ ] Fallback to uploaded template if Google Doc fails

### Merge Fields
- [ ] Basic merge: `[BUSINESS_NAME]`, `[CITY]`, `[PHONE]`
- [ ] Phone formatting: `[PHONE]` → "214-555-0100"
- [ ] Email links: `[EMAIL]` → clickable mailto link
- [ ] Phone links: `[PHONE_LINK]` → clickable tel link
- [ ] List generation: `[SERVICES_LIST]` → HTML list
- [ ] Conditional blocks: `[IF field=value]content[/IF]`

### Deployment
- [ ] HTML content sent to WordPress (Bridge Plugin mode)
- [ ] Elementor JSON sent to WordPress (direct mode)
- [ ] Both modes create valid Elementor pages
- [ ] Error handling for failed deployments

### Integration
- [ ] Works with existing RunPod image handling
- [ ] Works with existing phone normalization
- [ ] Works with existing smart corrections

---

## 🚀 Implementation Order

1. **Step 1:** Update CSV import to check for `page_content_doc_url`
2. **Step 2:** Add Google Doc fetching logic
3. **Step 3:** Enhance merge field function
4. **Step 4:** Update deployment function for Bridge Plugin mode
5. **Step 5:** Test with sample Google Doc
6. **Step 6:** Refine and optimize

---

## ⚠️ Important Notes

1. **Bridge Plugin:** Assumed to be installed on WordPress sites
2. **Google Doc Access:** Must be public ("Anyone with the link can VIEW")
3. **Error Handling:** Gracefully handle Google Doc fetch failures
4. **Backward Compatibility:** Keep existing Elementor JSON mode working
5. **Performance:** Consider caching Google Doc content for bulk imports

---

## 🔗 Related Files

- `modules/revpublish/backend/main.py` - Main import endpoint
- `modules/revpublish/backend/integrations/google_integrations.py` - Google Docs client
- `modules/revpublish/backend/wordpress_deploy.py` - WordPress deployment
- `modules/revpublish/backend/converters/elementor_converter.py` - Elementor conversion (Mode 2)

---

## 💡 Key Insights

1. **Two Modes:** HTML → Bridge Plugin (simpler) vs Direct Elementor JSON (more control)
2. **Google Docs:** Primary source for long-form content templates
3. **Merge Fields:** Support both simple `[FIELD]` and enhanced `[FIELD_LINK]` formats
4. **Bridge Plugin:** WordPress plugin handles HTML → Elementor conversion
5. **Flexibility:** Support both uploaded templates and Google Doc URLs

