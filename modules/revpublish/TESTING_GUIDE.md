# RevPublish Testing Guide
## How to Test Google Docs Integration & New Features

## 📋 Table of Contents
1. [UI Changes](#ui-changes)
2. [Test Files to Create](#test-files-to-create)
3. [Step-by-Step Testing](#step-by-step-testing)
4. [Expected Results](#expected-results)

---

## 🎨 UI Changes

### Updated Import Form
The import form now includes:
- ✅ **Bridge Plugin Mode** checkbox (NEW)
  - Default: Enabled (checked)
  - Description: "Send HTML content - Bridge Plugin converts to Elementor (Recommended)"
  - When checked: Uses Bridge Plugin mode (HTML → Bridge Plugin)
  - When unchecked: Uses Direct Elementor JSON mode

### Location
- **File**: `modules/revpublish/public/schemas/revpublish-import.json`
- **UI Path**: Navigate to `#import` tab in RevPublish dashboard

---

## 📁 Test Files to Create

### 1. Sample CSV File with Google Doc URLs

**File Name**: `test_google_docs_import.csv`

**Location**: Create in your project root or downloads folder

**Content**:
```csv
site_url,business_name,niche,city,state,phone,email,address,page_content_doc_url
test-site-1.com,Dallas Garage Experts,Garage Door Repair,Dallas,TX,2145550100,info@dallasgarage.com,"123 Main St, Dallas, TX 75201",https://docs.google.com/document/d/YOUR_DOC_ID_1/edit
test-site-2.com,Houston Plumbing Pros,Plumbing Services,Houston,TX,7135550200,contact@houstonplumbing.com,"456 Oak Ave, Houston, TX 77001",https://docs.google.com/document/d/YOUR_DOC_ID_2/edit
test-site-3.com,Austin Electric Co,Electrical Services,Austin,TX,5125550300,hello@austinelectric.com,"789 Pine Rd, Austin, TX 78701",
```

**Important Notes**:
- Replace `YOUR_DOC_ID_1` and `YOUR_DOC_ID_2` with actual Google Doc IDs
- The third row has NO `page_content_doc_url` to test fallback behavior
- Make sure Google Docs are set to "Anyone with the link can VIEW"

---

### 2. Sample Google Doc Template

**Steps to Create**:

1. **Go to Google Docs**: https://docs.google.com
2. **Create New Document**
3. **Add Content with Merge Fields**:

```
# Welcome to [BUSINESS_NAME]

We are [CITY]'s premier [NICHE] company, serving the community with excellence.

## Contact Us

📞 Call us: [PHONE_LINK]
✉️ Email: [EMAIL]
📍 Address: [ADDRESS]

## Our Services

[SERVICES_LIST]

## Why Choose Us?

- ✓ Licensed & Insured
- ✓ [YEARS_EXPERIENCE]+ Years of Experience
- ✓ Local Experts in [CITY]

[IF emergency_available=yes]
## 24/7 Emergency Service Available
Call us anytime for emergency [NICHE] services!
[/IF]

---

*Serving [CITY], [STATE] and surrounding areas*
```

4. **Set Document to Public**:
   - Click "Share" button (top right)
   - Click "Change to anyone with the link"
   - Set permission to "Viewer"
   - Click "Done"
   - Copy the document URL

5. **Get Document ID**:
   - URL format: `https://docs.google.com/document/d/DOCUMENT_ID/edit`
   - Copy the `DOCUMENT_ID` part
   - Use it in your CSV file

---

### 3. Sample CSV for Testing Merge Fields

**File Name**: `test_merge_fields.csv`

**Content**:
```csv
site_url,business_name,niche,city,state,phone,email,address,years_experience,services_offered,emergency_available,page_content_doc_url
demo-site.com,Test Business,Home Services,Test City,CA,5551234567,test@example.com,"123 Test St",15,"Service 1|||Service 2|||Service 3",yes,https://docs.google.com/document/d/YOUR_DOC_ID/edit
```

**Merge Fields Tested**:
- `[BUSINESS_NAME]` → "Test Business"
- `[CITY]` → "Test City"
- `[PHONE]` → "555-123-4567" (formatted)
- `[PHONE_LINK]` → Clickable tel link
- `[EMAIL]` → Clickable mailto link
- `[SERVICES_LIST]` → HTML list from `services_offered`
- `[IF emergency_available=yes]` → Conditional content

---

### 4. Sample CSV for Backward Compatibility Test

**File Name**: `test_backward_compat.csv`

**Content** (NO `page_content_doc_url` column):
```csv
site_url,business_name,niche,city,state,phone,email
legacy-site.com,Legacy Business,General Services,Legacy City,NY,2125559999,legacy@example.com
```

**Purpose**: Verify existing CSV imports still work without Google Docs

---

## 🧪 Step-by-Step Testing

### Test 1: Google Doc Integration

**Steps**:
1. Create a Google Doc with merge fields (see template above)
2. Set it to public ("Anyone with the link can VIEW")
3. Copy the document URL
4. Create CSV file with `page_content_doc_url` column
5. Open RevPublish dashboard → `#import` tab
6. Upload CSV file
7. Check "Bridge Plugin Mode" (should be checked by default)
8. Check "Preview Mode" (to test without deploying)
9. Click "Import"
10. Check results

**Expected**:
- ✅ Google Doc fetched successfully
- ✅ Merge fields replaced with CSV data
- ✅ Content source shows "Google Doc: [URL]"
- ✅ Deployment mode shows "Bridge Plugin (HTML)"

---

### Test 2: Enhanced Merge Fields

**Steps**:
1. Use `test_merge_fields.csv` with Google Doc template
2. Upload CSV
3. Check preview results

**Expected**:
- ✅ `[PHONE]` → Formatted as "555-123-4567"
- ✅ `[PHONE_LINK]` → Clickable `<a href="tel:5551234567">555-123-4567</a>`
- ✅ `[EMAIL]` → Clickable `<a href="mailto:test@example.com">test@example.com</a>`
- ✅ `[SERVICES_LIST]` → HTML `<ul><li>Service 1</li>...</ul>`
- ✅ `[IF emergency_available=yes]` → Shows emergency section

---

### Test 3: Fallback Behavior

**Steps**:
1. Use CSV with `page_content_doc_url` but invalid/non-existent URL
2. Upload CSV
3. Check results

**Expected**:
- ⚠️ Google Doc fetch fails
- ✅ Falls back to uploaded template file (if provided)
- ✅ Or falls back to basic HTML structure
- ✅ Error logged but import continues

---

### Test 4: Backward Compatibility

**Steps**:
1. Use `test_backward_compat.csv` (NO `page_content_doc_url` column)
2. Upload template file (optional)
3. Upload CSV
4. Check results

**Expected**:
- ✅ Works exactly as before
- ✅ Uses uploaded template file or basic structure
- ✅ All existing features work

---

### Test 5: Bridge Plugin vs Direct Elementor

**Steps**:
1. Upload CSV with Google Doc URL
2. **Test A**: Check "Bridge Plugin Mode" → Import
3. **Test B**: Uncheck "Bridge Plugin Mode" → Import

**Expected**:
- **Test A**: Sends HTML, Bridge Plugin converts
- **Test B**: Sends Elementor JSON directly

---

## 📊 Expected Results

### Successful Import Response

```json
{
  "status": "success",
  "timestamp": "2026-01-XX...",
  "preview_mode": true,
  "use_bridge_plugin": true,
  "summary": {
    "total_rows": 3,
    "successful_deployments": 3,
    "failed_deployments": 0,
    "auto_corrections": 1,
    "google_docs_fetched": 2,
    "google_docs_failed": 0
  },
  "corrections_summary": {
    "phone_normalized": 1
  },
  "deployments": [
    {
      "row_number": 1,
      "status": "preview",
      "content_source": "Google Doc: https://docs.google.com/document/d/...",
      "deployment_mode": "Bridge Plugin (HTML)",
      "site_info": {
        "site_url": "test-site-1.com",
        "business_name": "Dallas Garage Experts",
        "city": "Dallas",
        "state": "TX"
      },
      "merged_fields": {
        "BUSINESS_NAME": "Dallas Garage Experts",
        "PHONE": "214-555-0100",
        "EMAIL": "info@dallasgarage.com"
      }
    }
  ]
}
```

---

## 🔍 Verification Checklist

### Google Docs Integration
- [ ] CSV with `page_content_doc_url` processes correctly
- [ ] Google Doc HTML fetched successfully
- [ ] Merge fields replaced in Google Doc content
- [ ] Error handling works for invalid URLs
- [ ] Fallback to template file works
- [ ] Fallback to basic structure works

### Enhanced Merge Fields
- [ ] `[PHONE]` formats correctly (XXX-XXX-XXXX)
- [ ] `[PHONE_LINK]` creates clickable tel link
- [ ] `[EMAIL]` creates clickable mailto link
- [ ] `[SERVICES_LIST]` creates HTML list
- [ ] `[TESTIMONIALS_LIST]` creates testimonials HTML
- [ ] Conditional blocks `[IF field=value]` work

### Deployment Modes
- [ ] Bridge Plugin mode sends HTML
- [ ] Direct Elementor mode sends JSON
- [ ] Both modes create valid pages
- [ ] Mode selection works in UI

### Backward Compatibility
- [ ] CSV without `page_content_doc_url` works
- [ ] Template file upload works
- [ ] CSV-only mode works
- [ ] Existing merge fields work
- [ ] Phone normalization works

---

## 🐛 Troubleshooting

### Issue: Google Doc Fetch Fails (403 Error)
**Solution**: 
- Ensure Google Doc is set to "Anyone with the link can VIEW"
- Check URL format is correct
- Verify document ID in URL

### Issue: Merge Fields Not Replaced
**Solution**:
- Check CSV column names match merge field names (case-insensitive)
- Ensure merge fields use `[FIELD_NAME]` format
- Verify CSV has data in those columns

### Issue: Bridge Plugin Not Converting
**Solution**:
- Ensure Bridge Plugin is installed on WordPress site
- Check WordPress site credentials are correct
- Verify Bridge Plugin is active

### Issue: Import Fails with 500 Error
**Solution**:
- Check backend logs for detailed error
- Verify database connection
- Check WordPress REST API is accessible
- Ensure site credentials are correct

---

## 📝 Quick Test Checklist

1. ✅ Create Google Doc with merge fields
2. ✅ Set Google Doc to public
3. ✅ Create CSV with `page_content_doc_url` column
4. ✅ Upload CSV in RevPublish UI
5. ✅ Check "Preview Mode" first
6. ✅ Click "Import"
7. ✅ Review results
8. ✅ Test actual deployment (uncheck Preview Mode)

---

## 🎯 Next Steps After Testing

1. **Verify Results**: Check deployment results match expectations
2. **Test Real Deployment**: Deploy to actual WordPress site
3. **Check WordPress**: Verify pages created correctly
4. **Review Elementor**: Open pages in Elementor editor
5. **Test Bridge Plugin**: Verify HTML → Elementor conversion

---

## 📚 Related Files

- `modules/revpublish/public/schemas/revpublish-import.json` - UI schema
- `modules/revpublish/backend/main.py` - Backend implementation
- `modules/revpublish/IMPLEMENTATION_SUMMARY.md` - Implementation details

