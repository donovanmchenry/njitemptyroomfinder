# Deploying NJIT Empty Room Finder to Render

This guide will walk you through deploying the NJIT Empty Room Finder application to Render.

## Prerequisites

- A GitHub account with this repository pushed to GitHub
- A Render account (free tier works fine) - Sign up at https://render.com

## Step-by-Step Deployment Guide

### 1. Prepare Your Repository

Before deploying, make sure your code is pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Create a New Web Service on Render

1. Go to https://render.com and log in
2. Click on the **"New +"** button in the top right
3. Select **"Web Service"**
4. Connect your GitHub account if you haven't already
5. Find and select your `njitemptyroomfinder` repository

### 3. Configure Your Web Service

Fill in the following settings:

**Basic Settings:**
- **Name**: `njit-empty-room-finder` (or any name you prefer)
- **Region**: Choose the region closest to you
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave blank (unless your app is in a subdirectory)

**Build & Deploy Settings:**
- **Runtime**: `Python 3`
- **Build Command**:
  ```
  pip install -r requirements.txt && python parse_schedules.py
  ```
- **Start Command**:
  ```
  gunicorn app:app
  ```

**Instance Type:**
- **Free** (or choose a paid plan if you need more resources)

### 4. Environment Variables (Optional)

You shouldn't need any environment variables for basic deployment, but if you want to add any later:
1. Scroll down to the **"Environment Variables"** section
2. Click **"Add Environment Variable"**
3. Add your key-value pairs

Common environment variables you might want:
- `PYTHON_VERSION`: `3.11.0` (to specify Python version)

### 5. Deploy

1. Click **"Create Web Service"** at the bottom
2. Render will now:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Run `parse_schedules.py` to generate `schedule_data.json`
   - Start your Flask app with gunicorn
3. Wait for the deployment to complete (usually 2-5 minutes)

### 6. Access Your Application

Once deployed:
- Your app will be available at: `https://your-service-name.onrender.com`
- Render provides the full URL in the dashboard
- Click on the URL to open your application

## Important Notes

### Build Command Explained

The build command does two things:
```bash
pip install -r requirements.txt && python parse_schedules.py
```

1. **`pip install -r requirements.txt`** - Installs Flask, Flask-CORS, and gunicorn
2. **`python parse_schedules.py`** - Parses all CSV files in the `classes/` directory and generates `schedule_data.json`

This ensures that the schedule data is generated every time you deploy.

### Start Command Explained

```bash
gunicorn app:app
```

- **gunicorn** - Production-grade WSGI HTTP server (better than Flask's built-in server)
- **app:app** - Tells gunicorn to look for the Flask app in `app.py`
- Gunicorn automatically binds to the PORT environment variable that Render provides

### Free Tier Limitations

If using Render's free tier:
- Your service will spin down after 15 minutes of inactivity
- First request after inactivity may take 30-60 seconds (cold start)
- 750 hours of free runtime per month
- Consider upgrading to a paid plan for production use

## Troubleshooting

### Build Fails

**Problem**: Build fails with "No module named 'flask'"
**Solution**: Make sure `requirements.txt` is in the root directory and contains:
```
Flask==3.0.0
Flask-CORS==4.0.0
gunicorn==21.2.0
```

**Problem**: Build fails with "schedule_data.json not found"
**Solution**: Ensure the build command includes `python parse_schedules.py`

### Application Errors

**Problem**: Application crashes on startup
**Solution**: Check the logs in Render dashboard:
1. Go to your service
2. Click on "Logs" tab
3. Look for error messages

**Problem**: "No schedule_data.json file"
**Solution**:
- Make sure `classes/` directory with CSV files is committed to git
- Verify build command runs `parse_schedules.py`

### CSV Files Not Found

**Problem**: Parser can't find CSV files
**Solution**:
```bash
# Make sure CSV files are not in .gitignore
git add classes/*.csv
git commit -m "Add CSV schedule files"
git push
```

Then redeploy on Render.

## Updating Your Application

To deploy updates:

1. Make changes to your code locally
2. Test locally:
   ```bash
   python parse_schedules.py
   python app.py
   ```
3. Commit and push:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
4. Render will automatically detect the push and redeploy

## Custom Domain (Optional)

To use a custom domain:

1. In your Render service dashboard, go to **"Settings"**
2. Scroll to **"Custom Domains"**
3. Click **"Add Custom Domain"**
4. Follow the instructions to configure your DNS

## Monitoring

Render provides several monitoring features:

- **Logs**: Real-time application logs
- **Metrics**: CPU, memory usage, request counts
- **Events**: Deployment history and status

Access these from your service dashboard.

## Cost Optimization

For free tier:
- Service spins down after 15 minutes of inactivity
- Spins back up on first request (30-60 second delay)

For always-on service:
- Upgrade to Starter plan ($7/month)
- No spin-down delays
- Better performance

## Testing Your Deployment

Once deployed, test these endpoints:

1. **Homepage**:
   - URL: `https://your-app.onrender.com/`
   - Should show the web interface

2. **API - Get all rooms**:
   ```bash
   curl https://your-app.onrender.com/api/rooms
   ```

3. **API - Check available rooms**:
   ```bash
   curl -X POST https://your-app.onrender.com/api/available-rooms \
     -H "Content-Type: application/json" \
     -d '{"day": "Monday", "time": "14:00"}'
   ```

## Support

- **Render Documentation**: https://render.com/docs
- **Render Community**: https://community.render.com
- **This Project's Issues**: Check your GitHub repository issues

## Next Steps

After successful deployment, consider:

1. Setting up automatic deployments (already enabled by default)
2. Adding a custom domain
3. Enabling notifications for deploy events
4. Setting up health checks
5. Monitoring application performance

---

**Congratulations!** Your NJIT Empty Room Finder is now live on Render!
