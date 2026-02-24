# Quick Test Guide - RevPublish New Features

## 🎨 UI Changes Made

### Import Form Updates
**File**: `modules/revpublish/public/schemas/revpublish-import.json`

**New Checkbox Added**:
- ✅ **Bridge Plugin Mode** (🌉)
  - Default: Checked (enabled)
  - Description: "Send HTML content - Bridge Plugin converts to Elementor (Recommended)"
  - Location: Between "Preview Mode" and "Post Status" fields

**Updated Fields**:
- ✅ Preview Mode: Added description "Preview only - don't deploy to WordPress"
- ✅ Post Status: Added "Pending Review" option

---

## 📁 Test Files Created

### 1. `test_google_docs_import.csv`
**Location**: `modules/revpublish/test_google_docs_import.csv`

**Contains**:
- 3 test rows
- `page_content_doc_url` column with Google Doc URLs (replace `YOUR_DOC_ID_1` and `YOUR_DOC_ID_2`)
- All merge fields: business_name, city, phone, email, services_offered, etc.

**Usage**: Test Google Doc integration

---

### 2. `test_backward_compat.csv`
**Location**: `modules/revpublish/test_backward_compat.csv`

**Contains**:
- 1 test row
- NO `page_content_doc_url` column
- Basic fields only

**Usage**: Test backward compatibility (existing CSV imports)

---

### 3. `GOOGLE_DOC_TEMPLATE_EXAMPLE.md`
**Location**: `modules/revpublish/GOOGLE_DOC_TEMPLATE_EXAMPLE.md`

**Contains**:
- Complete Google Doc template with all merge fields
- Instructions on how to use it

**Usage**: Copy content into Google Doc for testing

---

## 🚀 Quick Start Testing

### Step 1: Create Google Doc

1. **Open**: https://docs.google.com
2. **Create New Document**
3. **Copy Content**: From `GOOGLE_DOC_TEMPLATE_EXAMPLE.md`
4. **Paste** into Google Doc
5. **Set to Public**:
   - Click "Share" → "Change to anyone with the link" → "Viewer" → "Done"
6. **Copy URL**: `https://docs.google.com/document/d/DOCUMENT_ID/edit`
7. **Extract Document ID**: The part between `/d/` and `/edit`

---

### Step 2: Update CSV File

1. **Open**: `test_google_docs_import.csv`
2. **Replace**: `YOUR_DOC_ID_1` with your actual Google Doc ID
3. **Replace**: `YOUR_DOC_ID_2` with another Google Doc ID (or same one)
4. **Save** the file

**Example**:
```csv
page_content_doc_url
https://docs.google.com/document/d/1a2b3c4d5e6f7g8h9i0j/edit
```

---

### Step 3: Test in UI

1. **Open RevPublish Dashboard**: Navigate to `#import` tab
2. **Upload CSV**: Click "Choose File" → Select `test_google_docs_import.csv`
3. **Check Options**:
   - ✅ Preview Mode (to test without deploying)
   - ✅ Bridge Plugin Mode (should be checked by default)
   - Select "Draft" status
4. **Click "Import"**
5. **Review Results**:
   - Check for "Google Doc: [URL]" in content_source
   - Verify merge fields were replaced
   - Check deployment_mode shows "Bridge Plugin (HTML)"

---

## ✅ What to Look For

### Successful Import Should Show:

```json
{
  "status": "success",
  "use_bridge_plugin": true,
  "summary": {
    "google_docs_fetched": 2,
    "google_docs_failed": 0
  },
  "deployments": [{
    "content_source": "Google Doc: https://docs.google.com/...",
    "deployment_mode": "Bridge Plugin (HTML)",
    "merged_fields": {
      "BUSINESS_NAME": "Dallas Garage Experts",
      "PHONE": "214-555-0100"
    }
  }]
}
```

---

## 🧪 Test Scenarios

### Test 1: Google Doc with Merge Fields ✅
- **File**: `test_google_docs_import.csv`
- **Expected**: Google Doc fetched, fields merged, HTML generated

### Test 2: Enhanced Merge Fields ✅
- **Check**: `[PHONE_LINK]` → Clickable tel link
- **Check**: `[EMAIL]` → Clickable mailto link
- **Check**: `[SERVICES_LIST]` → HTML list

### Test 3: Backward Compatibility ✅
- **File**: `test_backward_compat.csv`
- **Expected**: Works without `page_content_doc_url` column

### Test 4: Bridge Plugin Mode ✅
- **Checked**: Sends HTML (Bridge Plugin converts)
- **Unchecked**: Sends Elementor JSON directly

---

## 📝 Checklist

- [ ] UI shows "Bridge Plugin Mode" checkbox
- [ ] Google Doc URL in CSV is processed
- [ ] Merge fields replaced correctly
- [ ] Phone numbers formatted (XXX-XXX-XXXX)
- [ ] Phone links clickable
- [ ] Email links clickable
- [ ] Services list creates HTML list
- [ ] Preview mode works
- [ ] Actual deployment works (uncheck Preview)
- [ ] Backward compatibility works

---

## 🐛 Common Issues

**Issue**: Google Doc fetch fails (403)
- **Fix**: Ensure doc is set to "Anyone with the link can VIEW"

**Issue**: Merge fields not replaced
- **Fix**: Check CSV column names match merge field names

**Issue**: UI checkbox not showing
- **Fix**: Clear browser cache, refresh page

---

## 📚 Full Documentation

- `TESTING_GUIDE.md` - Complete testing guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `GOOGLE_DOC_TEMPLATE_EXAMPLE.md` - Template example

