# Frontend UI Fixes

## Issue: "Unknown element type: card" and "Unknown element type: button"

### Problem
The dashboard schema was using unsupported element types:
- `card` - Not supported by JSONRender
- `button` - Not supported by JSONRender

### Solution
Updated the schema to use supported element types:

1. **Stats Cards** → Changed to `statsGrid` with `cards` array
   - Uses `StatsGridElement` component
   - Supports dynamic data from `dataSource`
   - Each card has `label`, `dataKey`, and `color`

2. **Action Buttons** → Changed to `link` elements
   - Uses standard `<a>` tags
   - Supports `url`, `label`, `icon`, and `style`
   - Can navigate to hash routes (e.g., `#new-assessment`)

### Updated Schema Structure

**Before (Not Working):**
```json
{
  "type": "card",
  "children": [...]
}
{
  "type": "button",
  "text": "...",
  "action": {...}
}
```

**After (Working):**
```json
{
  "type": "statsGrid",
  "dataSource": {
    "endpoint": "/api/assessments/stats"
  },
  "cards": [
    {
      "label": "Assessments This Month",
      "dataKey": "total_assessments",
      "color": "#3b82f6"
    }
  ]
}
{
  "type": "link",
  "url": "#new-assessment",
  "label": "+ New Assessment",
  "icon": "➕"
}
```

### Supported Element Types

The JSONRender component supports:
- ✅ `container` - Layout container
- ✅ `header` - Headings (h1, h2, h3, etc.)
- ✅ `text` - Text content
- ✅ `statsGrid` - Stats cards grid
- ✅ `dataTable` - Data tables
- ✅ `link` - Links/buttons
- ✅ `form` - Forms
- ✅ `spacer` - Spacing
- ✅ `alert` - Alerts/notifications
- ✅ `badge` - Badges
- ❌ `card` - NOT SUPPORTED
- ❌ `button` - NOT SUPPORTED (use `link` instead)

### Files Updated

- `frontend/public/schemas/revscore-iq-dashboard.json` - Fixed to use supported types
- `public/schemas/revscore-iq-dashboard.json` - Copied for public access

### Testing

After refreshing the frontend:
1. ✅ Stats cards should display correctly
2. ✅ Action buttons should work as links
3. ✅ No more "Unknown element type" errors
4. ✅ Dashboard should load with data from API

