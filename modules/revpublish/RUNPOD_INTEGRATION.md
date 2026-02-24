# RunPod + ComfyUI Integration for RevPublish

## 🔗 Infrastructure Details

### RunPod Instance
- **ComfyUI URL**: `https://08wpyfo7aedg20-8188.proxy.runpod.net/`
- **Console URL**: `https://console.runpod.io/pods?id=08wpyfo7aedg20`
- **SSH Access**: Configured with ed25519 key
- **API Key**: `(set RUNPOD_API_KEY in environment - do not commit)` (Valid until 02-01-2026)

### Purpose
RunPod instance hosts ComfyUI for AI image generation. Images are:
1. Generated via ComfyUI on RunPod
2. Stored in `/workspace/media` on RunPod
3. Referenced by filename in CSV data
4. Uploaded to WordPress during deployment

---

## 📁 Current Implementation

### File: `modules/revpublish/backend/wordpress_deploy.py`

**Key Functions:**

1. **`get_local_image_path(filename: str)`**
   - Locates image files in RunPod workspace
   - Searches `/workspace/media` and subdirectories
   - Returns full path if found

2. **`process_runpod_assets(row_data: dict)`**
   - Processes assets for a CSV row
   - Handles:
     - `hero_image_filename` → Hero image
     - `gallery_images` → Gallery image array
   - Returns asset map with local paths

3. **`sideload_image_to_wp(site: dict, local_path: str, filename: str)`**
   - Uploads image from RunPod to WordPress Media Library
   - Uses WordPress REST API (`/wp/v2/media`)
   - Returns WordPress attachment ID

---

## 🔧 Configuration

### Environment Variables

```bash
# RunPod media storage location
RUNPOD_MEDIA_PATH=/workspace/media

# RunPod API (if needed for direct access)
RUNPOD_API_KEY=<set in environment - do not commit>
RUNPOD_ENDPOINT=https://08wpyfo7aedg20-8188.proxy.runpod.net/
```

### CSV Column Support

**Image Filename Columns:**
- `hero_image_filename` - Main hero image
- `gallery_images` - Comma or pipe-delimited list of image filenames

**Example CSV Row:**
```csv
site_url,business_name,hero_image_filename,gallery_images
example.com,My Business,hero-123.jpg,"img1.jpg,img2.jpg,img3.jpg"
```

---

## 🚀 Integration Workflow

### Step 1: Image Generation (ComfyUI)
1. Images generated via ComfyUI on RunPod
2. Saved to `/workspace/media/` directory
3. Filenames recorded (e.g., `hero-123.jpg`)

### Step 2: CSV Preparation
1. Add image filenames to CSV:
   - `hero_image_filename` column
   - `gallery_images` column (optional)

### Step 3: Deployment Process
1. RevPublish reads CSV row
2. Calls `process_runpod_assets(row_data)`
3. Locates images in RunPod workspace
4. Uploads each image to WordPress via `sideload_image_to_wp()`
5. Gets WordPress attachment IDs
6. Includes image IDs in Elementor JSON

### Step 4: Elementor Page Creation
1. Elementor JSON includes image widgets
2. Image widgets reference WordPress attachment IDs
3. Page deployed with images embedded

---

## 📝 Implementation Notes

### Current Status
✅ RunPod image path resolution
✅ Image upload to WordPress
✅ Asset processing for CSV rows
✅ Hero and gallery image support

### Missing Features
⚠️ ComfyUI API integration (if direct generation needed)
⚠️ Image optimization before upload
⚠️ Alt text generation for images
⚠️ Image metadata extraction

---

## 🔐 Security Considerations

1. **SSH Access**: Use provided ed25519 key for RunPod SSH
2. **API Key**: Store securely in environment variables
3. **File Permissions**: Ensure RunPod workspace is accessible
4. **WordPress Credentials**: Use application passwords, not regular passwords

---

## 🧪 Testing

### Test Image Upload
```python
from wordpress_deploy import process_runpod_assets, sideload_image_to_wp

# Test asset processing
row_data = {
    'hero_image_filename': 'test-hero.jpg',
    'gallery_images': ['img1.jpg', 'img2.jpg']
}

assets = process_runpod_assets(row_data)
print(assets)  # Should show local paths

# Test WordPress upload
site = {
    'wp_api_url': 'https://example.com/wp-json/wp/v2',
    'wp_username': 'admin',
    'wp_app_password': 'xxxx xxxx xxxx xxxx'
}

attachment_id = await sideload_image_to_wp(
    site, 
    assets['hero_image']['local_path'],
    assets['hero_image']['filename']
)
print(f"Uploaded as attachment ID: {attachment_id}")
```

---

## 📌 Next Steps

1. **Verify RunPod Access**
   - Test SSH connection
   - Verify `/workspace/media` directory exists
   - Check file permissions

2. **Test Image Processing**
   - Generate test image via ComfyUI
   - Verify filename in CSV
   - Test upload to WordPress

3. **Integrate with CSV Import**
   - Ensure `process_runpod_assets()` is called during import
   - Verify images are uploaded before page deployment
   - Test Elementor page with images

4. **Add Error Handling**
   - Handle missing images gracefully
   - Log image upload failures
   - Provide clear error messages

---

## 🔗 Related Files

- `modules/revpublish/backend/wordpress_deploy.py` - Main deployment logic
- `modules/revpublish/backend/main.py` - CSV import endpoint
- `modules/revpublish/backend/converters/elementor_converter.py` - Elementor JSON generation

---

## 💡 Usage Example

```python
# In CSV import endpoint
for index, row in df.iterrows():
    row_dict = row.to_dict()
    
    # Process RunPod assets
    asset_map = process_runpod_assets(row_dict)
    
    # Upload images to WordPress
    if asset_map.get('hero_image'):
        hero_attachment_id = await sideload_image_to_wp(
            site,
            asset_map['hero_image']['local_path'],
            asset_map['hero_image']['filename']
        )
        # Include in Elementor JSON
        elementor_data['hero_image_id'] = hero_attachment_id
    
    # Deploy page with images
    deploy_to_elementor(site, row_dict, asset_map)
```

