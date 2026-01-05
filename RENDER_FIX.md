# Render Deployment Fix Guide

## Issue: Still Using Python 3.13

Even with runtime.txt, Render may default to Python 3.13. Here's how to fix it:

### Option 1: Set Python Version in Render Dashboard (EASIEST)

1. Go to your Render dashboard
2. Click on your web service
3. Go to "Environment" tab
4. Add environment variable:
   ```
   PYTHON_VERSION=3.11.8
   ```
5. Click "Save Changes"
6. Trigger manual deploy

### Option 2: Update runtime.txt Format

Make sure your `runtime.txt` contains EXACTLY:
```
python-3.11.8
```

(Not `python-3.11` or `python-3.11.0`)

### Option 3: Use .python-version File

Create `.python-version` in root:
```
3.11.8
```

### After Fixing

1. Commit and push changes:
   ```bash
   git add .
   git commit -m "Fix: Force Python 3.11.8"
   git push
   ```

2. In Render dashboard:
   - Go to your service
   - Click "Manual Deploy" → "Deploy latest commit"
   - Watch build logs

3. Verify Python version in logs:
   - Should see: "Using Python version 3.11.8"
   - NOT: "Using Python version 3.13.x"

### Why This Happens

- Render's default Python is 3.13
- runtime.txt format must be exact
- Environment variable overrides everything
- Newer pydantic works with Python 3.13 (updated requirements.txt)

### If Still Failing

Try downgrading pydantic in requirements.txt:
```
pydantic==2.5.0
pydantic-core==2.14.0
```

These versions have pre-built wheels for all Python versions.
