# RevPublish Animation Manager - Standard Operating Procedure

**Module:** RevPublish (Module 9)
**Feature:** Animation Template Manager
**Version:** 1.0.0
**Last Updated:** 2026-02-18
**URL:** https://automation.smarketsherpa.ai/revflow_os/revpublish/#animation

---

## Table of Contents

1. [Overview](#overview)
2. [Accessing the Animation Manager](#accessing-the-animation-manager)
3. [Understanding Animation Types](#understanding-animation-types)
4. [Browsing Templates](#browsing-templates)
5. [Deploying Animations](#deploying-animations)
6. [Performance Analytics](#performance-analytics)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Overview

The Animation Manager allows you to browse, configure, and deploy Elementor-compatible CSS animations across your WordPress site portfolio. With 626 pre-built animation templates organized by type and page purpose, you can enhance user engagement without writing custom code.

### Key Features

- **626 Animation Templates** - Pre-configured entrance animations
- **5 Animation Types** - Fade, Slide, Zoom, Bounce, Scroll-triggered
- **4 Page Types** - Landing, Service, Location, Blog
- **Bulk Deployment** - Deploy to multiple sites simultaneously
- **Performance Scoring** - Each template rated for page load impact

---

## Accessing the Animation Manager

### Direct URL
```
https://automation.smarketsherpa.ai/revflow_os/revpublish/#animation
```

### From RevPublish Dashboard
1. Navigate to RevPublish dashboard
2. Click the **"Animation"** tab in the navigation bar

### From RevFlow OS
1. Go to RevFlow OS main dashboard (port 3000)
2. Click Module 9: RevPublish
3. Select "Animation" from the tabs

---

## Understanding Animation Types

### Fade Animations
| Animation | Description | Best For |
|-----------|-------------|----------|
| `fadeIn` | Simple opacity fade | Universal, subtle entrance |
| `fadeInUp` | Fade while moving up | Hero sections, CTAs |
| `fadeInDown` | Fade while moving down | Headers, notifications |
| `fadeInLeft` | Fade from left | Sidebars, secondary content |
| `fadeInRight` | Fade from right | Feature highlights |

**Performance Impact:** Low (45ms avg)
**Recommended For:** Professional sites, corporate pages

### Slide Animations
| Animation | Description | Best For |
|-----------|-------------|----------|
| `slideInLeft` | Slide from left edge | Navigation, menus |
| `slideInRight` | Slide from right edge | Cards, testimonials |
| `slideInUp` | Slide from bottom | Footers, popups |
| `slideInDown` | Slide from top | Banners, alerts |

**Performance Impact:** Medium (62ms avg)
**Recommended For:** Dynamic content, interactive elements

### Zoom Animations
| Animation | Description | Best For |
|-----------|-------------|----------|
| `zoomIn` | Scale up from center | Images, modals |
| `zoomInUp` | Zoom while moving up | Product cards |
| `zoomInDown` | Zoom while moving down | Dropdown content |
| `zoomInLeft` | Zoom from left | Gallery items |
| `zoomInRight` | Zoom from right | Feature boxes |

**Performance Impact:** Medium-High (78ms avg)
**Recommended For:** E-commerce, portfolios, galleries

### Bounce Animations
| Animation | Description | Best For |
|-----------|-------------|----------|
| `bounceIn` | Playful bounce entrance | CTAs, buttons |
| `bounceInUp` | Bounce from bottom | Notifications |
| `bounceInDown` | Bounce from top | Alerts, badges |
| `bounceInLeft` | Bounce from left | Social proof |
| `bounceInRight` | Bounce from right | Testimonials |

**Performance Impact:** Medium-High (85ms avg)
**Recommended For:** Casual brands, youth-oriented sites

### Scroll-Triggered Animations
Any animation can be scroll-triggered, meaning it activates when the element enters the viewport.

**Performance Impact:** Low (35ms avg - deferred loading)
**Recommended For:** Long-form content, landing pages

---

## Browsing Templates

### Template Table Columns

| Column | Description |
|--------|-------------|
| **ID** | Unique template identifier (use for API calls) |
| **Template Name** | Descriptive name including animation type |
| **Type** | Animation category (fade/slide/zoom/bounce/scroll) |
| **Page Type** | Target page type (landing/service/location/blog) |
| **Score** | Performance score (higher = faster load) |
| **Uses** | Number of times deployed across portfolio |

### Filtering Templates

Use the API directly for filtered results:

```bash
# Get fade animations only
/api/animation/templates?animation_type=fade

# Get landing page templates
/api/animation/templates?page_type=landing

# Get high-performance templates (score 90+)
/api/animation/templates?min_performance=90

# Combined filters
/api/animation/templates?animation_type=fade&page_type=service&min_performance=80
```

### Selecting a Template

1. Review the template table
2. Note the **Template ID** of your chosen animation
3. Check the **Performance Score** (aim for 80+ for production)
4. Verify the **Page Type** matches your target pages

---

## Deploying Animations

### Quick Deploy Form

Located on the right side of the Animation Manager page.

#### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Template ID** | The numeric ID from the templates table | `5` |
| **Site IDs** | Comma-separated list of WordPress site IDs | `1, 2, 3` or `1,2,3` |

#### Optional Configuration

| Field | Default | Options |
|-------|---------|---------|
| **Entrance Animation** | fadeIn | Any valid animation name |
| **Duration (ms)** | 800 | 200-2000 |
| **Scroll Triggered** | Yes | Yes/No |

### Deployment Steps

1. **Select Template**
   - Browse the templates table
   - Find a suitable animation for your use case
   - Copy the Template ID

2. **Identify Target Sites**
   - Go to the "Sites" tab to see your WordPress sites
   - Note the Site IDs you want to deploy to
   - Use comma-separated values for multiple sites

3. **Configure Animation**
   - Enter Template ID in the form
   - Enter Site IDs (e.g., `1, 5, 12, 23`)
   - Optionally adjust:
     - Entrance animation override
     - Duration (default 800ms is recommended)
     - Scroll trigger setting

4. **Deploy**
   - Click "Deploy Animation"
   - Watch for success/error message
   - Check Queue tab for deployment status

### Bulk Deployment via API

For deploying to many sites programmatically:

```bash
curl -X POST https://automation.smarketsherpa.ai/revflow_os/revpublish/api/animation/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 5,
    "site_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "config": {
      "entrance_animation": "fadeInUp",
      "animation_duration": 800,
      "animation_delay": 0,
      "scroll_triggered": true,
      "viewport_offset": "20%"
    }
  }'
```

---

## Performance Analytics

### Metrics Displayed

The Performance Analytics section shows:

| Metric | Description |
|--------|-------------|
| **Animation Type** | Category of animation |
| **Template Count** | Number of templates in category |
| **Avg. Score** | Average performance score |
| **Total Uses** | Total deployments across all sites |

### Understanding Performance Scores

| Score Range | Rating | Recommendation |
|-------------|--------|----------------|
| 90-100 | Excellent | Use freely, minimal impact |
| 80-89 | Good | Safe for most use cases |
| 70-79 | Acceptable | Use sparingly on mobile |
| Below 70 | Caution | Test thoroughly before production |

### Performance by Animation Type (Typical)

| Type | Avg Load Impact | Best Score | Worst Score |
|------|-----------------|------------|-------------|
| Scroll | 35ms | 95 | 75 |
| Fade | 45ms | 95 | 70 |
| Slide | 62ms | 90 | 72 |
| Zoom | 78ms | 94 | 70 |
| Bounce | 85ms | 87 | 70 |

---

## Best Practices

### DO ✅

1. **Start with Fade animations** - Lowest performance impact, most professional
2. **Use scroll-triggered** - Defers animation until visible, improves initial load
3. **Keep duration 600-1000ms** - Sweet spot for perceived smoothness
4. **Test on mobile first** - Animations hit mobile performance harder
5. **Match animation to content** - Subtle for professional, dynamic for casual
6. **Use consistent animations** - Same type throughout a page section
7. **Prioritize above-fold content** - Use fastest animations for hero sections

### DON'T ❌

1. **Don't animate everything** - Pick 3-5 key elements per page
2. **Don't use bounce for professional sites** - Can feel unprofessional
3. **Don't exceed 1200ms duration** - Feels sluggish
4. **Don't mix too many animation types** - Creates visual chaos
5. **Don't animate on scroll AND on load** - Pick one trigger
6. **Don't use zoom on text-heavy elements** - Hard to read during animation
7. **Don't deploy to production without testing** - Always preview first

### Page Type Guidelines

| Page Type | Recommended Animations | Avoid |
|-----------|----------------------|-------|
| **Landing** | fadeInUp, slideInUp, zoomIn | bounceIn (unless casual brand) |
| **Service** | fadeIn, slideInLeft/Right | Excessive zoom |
| **Location** | fadeIn, subtle slides | Bounce, aggressive zoom |
| **Blog** | fadeIn, fadeInUp | Distracting animations |

---

## Troubleshooting

### "No data available" in Templates Table

1. **Hard refresh the page:** Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. **Check API status:**
   ```bash
   curl https://automation.smarketsherpa.ai/revflow_os/revpublish/api/animation/templates?per_page=1
   ```
3. **Clear browser cache** and reload

### Deployment Shows "Queued" but Doesn't Complete

1. Check the Queue tab for status
2. Verify site credentials are valid (Sites tab)
3. Check container logs:
   ```bash
   docker logs revflow-module09-revpublish --tail 50
   ```

### Animation Not Appearing on WordPress Site

1. Verify deployment status is "completed"
2. Check if Elementor is active on the target site
3. Clear WordPress cache (if using caching plugin)
4. Clear CDN cache if applicable

### Performance Score Seems Wrong

Performance scores are calculated based on:
- Animation complexity
- Typical browser rendering time
- CSS property changes involved

Actual performance varies by:
- User's device
- Browser version
- Other page elements

---

## API Reference

### List Templates
```
GET /api/animation/templates
```

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `animation_type` | string | Filter by type (fade/slide/zoom/bounce/scroll) |
| `page_type` | string | Filter by page type (landing/service/location/blog) |
| `min_performance` | int | Minimum performance score |
| `page` | int | Page number (default: 1) |
| `per_page` | int | Results per page (default: 50, max: 100) |

### Get Template Details
```
GET /api/animation/templates/{template_id}
```

### Deploy Animation
```
POST /api/animation/deploy
```

**Body:**
```json
{
  "template_id": 5,
  "site_ids": [1, 2, 3],
  "config": {
    "entrance_animation": "fadeIn",
    "animation_duration": 800,
    "animation_delay": 0,
    "scroll_triggered": true,
    "viewport_offset": "20%"
  }
}
```

### Get Queue Status
```
GET /api/queue
```

### Get Performance Analytics
```
GET /api/analytics/animation-performance
```

### Get Stats Summary
```
GET /api/animation/stats
```

---

## Support

For issues with the Animation Manager:

1. Check this SOP first
2. Review container logs: `docker logs revflow-module09-revpublish`
3. Verify API health: `curl http://localhost:8550/health`
4. Contact RevFlow OS support

---

**Document Version:** 1.0.0
**Module:** RevPublish (Module 9)
**Port:** 8550 (Backend) | Frontend via Nginx
**Container:** revflow-module09-revpublish
