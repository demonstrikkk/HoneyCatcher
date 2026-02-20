# 🚨 URGENT FIX - CORS Error Resolution

## The Problem
```
Access to XMLHttpRequest at 'https://honeycatcher.onrender.com/api/sessions' 
from origin 'https://honeycatcher-1.onrender.com' has been blocked by CORS policy
```

## The Solution

### ✅ Step 1: Update Render Environment Variable (CRITICAL)

1. Go to **Render Dashboard** → https://dashboard.render.com
2. Click on your **Backend Service** (honeycatcher or similar)
3. Click **Environment** in the left sidebar
4. Find or Add the variable: `CORS_ORIGINS`
5. Set the value to:
```
http://localhost:5173,http://localhost:3000,http://localhost:8000,https://honeycatcher.onrender.com,https://honeycatcher-1.onrender.com
```

⚠️ **IMPORTANT**: Include ALL your frontend URLs:
- `https://honeycatcher-1.onrender.com` (your current frontend)
- `https://honeycatcher.onrender.com` (if you have another frontend)
- Any other frontend domains you use

### ✅ Step 2: Save and Redeploy

1. Click **Save Changes** in Render
2. The service will automatically redeploy
3. Wait 2-3 minutes for the deploy to complete

### ✅ Step 3: Verify the Fix

Open your deployed frontend and check the browser console:
```javascript
// Should now work without CORS errors!
fetch('https://honeycatcher.onrender.com/api/sessions')
  .then(r => r.json())
  .then(console.log);
```

---

## Alternative: Allow All Origins (Quick Fix - Not Recommended for Production)

If you want to temporarily allow ALL origins:

1. Set `CORS_ORIGINS` to: `*`
2. Redeploy

⚠️ **WARNING**: This allows any website to call your API. Use only for testing!

---

## Local Development

Your local backend `.env` has been updated. To test locally:

```bash
cd honeypot/backend
python -m uvicorn main:app --reload
```

Check logs for:
```
🌐 CORS allowed origins: ['http://localhost:5173', ...]
```

---

## Additional Fixes Applied

### 1. Improved CORS Parsing
- Now strips whitespace from origin URLs
- Better handling of comma-separated values
- Added logging to see allowed origins

### 2. Voice Upload 500 Error
If you still see voice upload errors after fixing CORS, check:
- MongoDB connection is working
- Audio file format is correct (WAV, MP3, WebM)
- File size is under limit

---

## Quick Checklist

- [ ] Updated `CORS_ORIGINS` on Render Dashboard
- [ ] Clicked "Save Changes" 
- [ ] Waited for redeploy to complete (2-3 min)
- [ ] Refreshed frontend page (hard refresh: Ctrl+Shift+R)
- [ ] Checked browser console - no CORS errors
- [ ] Tested API calls - working correctly

---

## Still Having Issues?

### Check Backend Logs on Render
1. Go to Render Dashboard → Backend Service → Logs
2. Look for:
   ```
   🌐 CORS allowed origins: [...]
   ```
3. Verify your frontend URL is in the list

### Check Browser Console
1. Press F12 → Console tab
2. Look for CORS errors
3. Check the "Origin" in the error message
4. Make sure that origin is in CORS_ORIGINS

### Test Backend Health
```bash
curl https://honeycatcher.onrender.com/health
# Should return: {"status":"ok","db":"connected"}
```

---

## What Changed

**Files Updated:**
- `honeypot/backend/.env` - Added `honeycatcher-1.onrender.com` to CORS_ORIGINS
- `honeypot/backend/main.py` - Improved CORS parsing and added logging

**What You Need to Do:**
- Update CORS_ORIGINS environment variable on Render Dashboard
- Redeploy backend service

That's it! Your CORS errors will be fixed. 🎉
