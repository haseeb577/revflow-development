# WordPress Site Discovery Setup Guide

This guide explains how to connect WordPress sites to RevPublish using the direct WordPress connection method.

## Method 1: Using RevPublish Connector Plugin (Recommended)

### Step 1: Install the Plugin

1. Download the `revpublish-connector.php` file from `modules/revpublish/wordpress-plugin/`
2. Upload it to your WordPress site:
   - Option A: Via WordPress Admin
     - Go to **Plugins → Add New → Upload Plugin**
     - Select the `revpublish-connector.php` file
     - Click **Install Now** and **Activate**
   
   - Option B: Via FTP/SFTP
     - Upload `revpublish-connector.php` to `/wp-content/plugins/revpublish-connector/`
     - Go to WordPress Admin → Plugins → Activate "RevPublish Connector"

### Step 2: Get Site Credentials

1. After activation, go to **Settings → RevPublish** in WordPress admin
2. You'll see:
   - **Site ID**: Unique identifier for your site
   - **Site Secret**: Secret key for API authentication
   - **API Endpoint**: The REST API endpoint URL

3. Copy the **Site Secret** (you'll need it in RevPublish portal)

### Step 3: Register Site in RevPublish

1. Open RevPublish portal → **Sites** tab
2. Scroll to **"🔍 Discover WordPress Sites"** section
3. Enter:
   - **WordPress Site URL**: Your site URL (e.g., `https://yoursite.com`)
   - **Site Secret**: The secret from plugin settings
   - Leave username/password empty (not needed with plugin)
4. Click **"🔍 Discover & Register Site"**
5. The site will be automatically discovered and registered!

## Method 2: Using WordPress Application Passwords

If you prefer not to install the plugin, you can use WordPress built-in Application Passwords:

### Step 1: Create Application Password

1. Log into your WordPress site at `yoursite.com/wp-admin`
2. Go to **Users → Profile**
3. Scroll to **Application Passwords** section
4. Enter name: `RevPublish`
5. Click **Add New Application Password**
6. **IMPORTANT**: Copy the password immediately (shown only once!)
   - Format: `xxxx xxxx xxxx xxxx xxxx xxxx`
   - **Remove all spaces** when entering in RevPublish!

### Step 2: Register Site in RevPublish

1. Open RevPublish portal → **Sites** tab
2. Scroll to **"🔍 Discover WordPress Sites"** section
3. Enter:
   - **WordPress Site URL**: Your site URL
   - **WordPress Username**: Your admin username
   - **Application Password**: The password you copied (without spaces!)
   - Leave Site Secret empty
4. Click **"🔍 Discover & Register Site"**

## How It Works

### Plugin Method (Method 1)
- Plugin creates a REST API endpoint: `/wp-json/revpublish/v1/site-info`
- RevPublish connects to this endpoint using the Site Secret
- No WordPress credentials needed
- More secure (secret-based authentication)

### Application Password Method (Method 2)
- Uses WordPress built-in REST API
- Requires WordPress username and Application Password
- Works with any WordPress site (no plugin needed)
- Standard WordPress authentication

## API Endpoints

The plugin provides these endpoints:

- `GET /wp-json/revpublish/v1/site-info` - Get site information
- `GET /wp-json/revpublish/v1/health` - Health check (public)
- `POST /wp-json/revpublish/v1/register` - Register with portal

## Troubleshooting

### Error: "WordPress site not found"
- Check that the site URL is correct
- Ensure the site is accessible (not behind firewall)
- If using plugin, verify it's activated

### Error: "Failed to connect"
- Check SSL certificate (self-signed certs may fail)
- Verify site is publicly accessible
- Check if site requires authentication to access

### Plugin not showing in WordPress
- Verify file is in `/wp-content/plugins/revpublish-connector/`
- Check file permissions (should be readable)
- Ensure PHP version is 7.4 or higher

### Application Password not working
- **CRITICAL**: Remove all spaces from password!
- Verify username is correct
- Check that Application Password was created correctly
- Ensure WordPress version is 5.6+ (Application Passwords feature)

## Security Notes

- **Site Secret**: Keep this secret! Don't share it publicly
- **Application Passwords**: Can be revoked from WordPress admin
- Both methods use secure authentication
- Plugin method is more secure (no WordPress credentials needed)

## Bulk Discovery

To discover multiple sites at once, you can use the API endpoint:

```
POST /api/wordpress/discover-bulk?urls=site1.com,site2.com,site3.com
```

This will attempt to discover all sites and return results for each.

