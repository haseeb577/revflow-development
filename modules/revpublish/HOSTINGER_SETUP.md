# Hostinger Integration Setup Guide

This guide explains how to configure RevPublish to fetch websites dynamically from your Hostinger account.

## Option 1: Using Hostinger API (If Available)

### Step 1: Get Hostinger API Credentials

1. Log into your Hostinger account
2. Navigate to API settings (usually under Account → API or Developer Settings)
3. Generate an API key/token
4. Copy the API key

### Step 2: Configure Environment Variables

Add to your `.env` file:

```env
HOSTINGER_API_KEY=your_api_key_here
HOSTINGER_API_URL=https://api.hostinger.com/v1
```

### Step 3: Test the Integration

1. Restart the backend server
2. Open the Sites tab in RevPublish
3. Click "🔄 Sync from Hostinger" button
4. Websites should appear in the selector

## Option 2: Manual Sync (If No API Available)

If Hostinger doesn't provide a public API:

### Method A: Export from Hostinger Control Panel

1. Log into Hostinger hPanel
2. Go to Domains section
3. Export your domains list (if export feature exists)
4. Use the CSV import feature in RevPublish

### Method B: Use Local Database

The system will automatically fallback to your local database if no Hostinger API key is configured.

## API Endpoints

- `GET /api/hostinger/websites` - Fetch all websites from Hostinger
- `POST /api/hostinger/sync` - Sync Hostinger websites to local database

## Troubleshooting

### Error: "Hostinger API key not configured"
- Add `HOSTINGER_API_KEY` to your `.env` file
- Restart the backend server

### Error: "Failed to connect to Hostinger API"
- Check if Hostinger provides a public API
- Verify the API URL is correct
- Check your API key is valid

### No websites showing
- The system will fallback to local database
- Use "Sync from Hostinger" button to import websites
- Or manually add websites using the form

## Notes

- Hostinger may not have a public API for fetching domains
- If API is not available, use the local database and manual entry
- The sync button will attempt to fetch from Hostinger and store in local database

