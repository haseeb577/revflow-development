# How to Find the "Discover WordPress Sites" Form

## Location in RevPublish UI

The "Discover WordPress Sites" form is located in the **Sites** tab of RevPublish.

### Step-by-Step Navigation:

1. **Open RevPublish Portal**
   - Navigate to your RevPublish portal URL
   - Example: `http://localhost:3550/revflow_os/revpublish`

2. **Click on "Sites" Tab**
   - Look for the navigation tabs at the top
   - Click on the **"Sites"** tab (or **"Sites"** menu item)

3. **Scroll Down on the Sites Page**
   - The page contains several sections in this order:
     - **🌐 WordPress Sites Portfolio** (header)
     - **🔐 How to Create Application Passwords** (instructions)
     - **🔍 Discover WordPress Sites** ← **THIS IS THE FORM YOU NEED**
     - **✏️ Update Site Credentials** (form to update existing sites)
     - **📊 All Sites** (table showing all registered sites)

4. **Look for the Green Header**
   - The "Discover WordPress Sites" section has a **green header** (🔍 emoji)
   - It's in a dark gray container box
   - Located **after** the "How to Create Application Passwords" section
   - Located **before** the "Update Site Credentials" section

## Visual Layout:

```
┌─────────────────────────────────────────┐
│  🌐 WordPress Sites Portfolio          │
│  (Header)                                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🔐 How to Create Application Passwords │
│  (Instructions section)                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  🔍 Discover WordPress Sites             │ ← FIND THIS!
│                                         │
│  [WordPress Site URL input]             │
│  [Site Secret input]                     │
│  [WordPress Username input]              │
│  [Application Password input]           │
│  [🔍 Discover & Register Site button]    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  ✏️ Update Site Credentials             │
│  (Form to update existing sites)         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  📊 All Sites (X)                       │
│  (Table of all sites)                    │
└─────────────────────────────────────────┘
```

## If You Can't See It:

### Option 1: Check Browser Console
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Look for any errors related to:
   - Schema loading
   - API calls
   - Component rendering

### Option 2: Check Schema File
The form is defined in:
```
modules/revpublish/frontend/src/schemas/revpublish-sites.json
```
At line 75-146

### Option 3: Hard Refresh
1. Press `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac)
2. This clears cache and reloads the schema

### Option 4: Direct URL
Try accessing the schema directly:
```
http://localhost:3550/revflow_os/revpublish/schemas/revpublish-sites.json
```

## Form Fields:

When you find the form, you'll see these fields:

1. **🌐 WordPress Site URL** (Required)
   - Enter: `https://yoursite.com` or `yoursite.com`

2. **🔐 Site Secret** (Optional)
   - Only if you installed the RevPublish Connector plugin
   - Get it from WordPress Admin → Settings → RevPublish

3. **👤 WordPress Username** (Optional)
   - Your WordPress admin username
   - Required if NOT using the plugin

4. **🔑 Application Password** (Optional)
   - WordPress Application Password
   - Create in WordPress → Users → Profile → Application Passwords
   - **Remove all spaces!**

5. **🔍 Discover & Register Site** (Button)
   - Click to discover and register the site

## Quick Test:

1. Open Sites tab
2. Scroll down past the "How to Create Application Passwords" section
3. Look for a section with green header "🔍 Discover WordPress Sites"
4. You should see a form with 4 input fields and a submit button

If you still can't find it, check the browser console for errors or let me know what you see on the Sites page!

