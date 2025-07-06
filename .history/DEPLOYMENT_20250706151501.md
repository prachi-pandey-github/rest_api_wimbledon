# Deploying Wimbledon API to Render

This guide will help you deploy your Flask API with Redis to Render.

## Prerequisites

1. **GitHub Account**: Your code needs to be in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/wimbledon-api.git
   git push -u origin main
   ```

2. **Connect to Render**:
   - Go to [render.com](https://render.com) and sign in
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file

3. **Deploy**:
   - Review the services (Redis + Web App)
   - Click "Apply"
   - Wait for deployment to complete

### Option 2: Manual Setup

#### Step 1: Create Redis Service
1. In Render dashboard, click "New" → "Redis"
2. Choose:
   - Name: `wimbledon-redis`
   - Plan: Starter (Free)
   - Region: Choose closest to your users
3. Click "Create Redis"

#### Step 2: Create Web Service
1. Click "New" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `wimbledon-api`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT main:app`
   - **Plan**: Starter (Free)

#### Step 3: Configure Environment Variables
Add these environment variables in the web service settings:

- `FLASK_ENV`: `production`
- `REDIS_URL`: Copy from your Redis service connection string
- `SECRET_KEY`: Generate a secure random key

#### Step 4: Set Health Check
- **Health Check Path**: `/health`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_ENV` | Flask environment (production) | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | Flask secret key | Yes |
| `PORT` | Port number (set by Render) | Auto |

## Post-Deployment

### 1. Test Your API
Your API will be available at: `https://your-service-name.onrender.com`

Test endpoints:
- Health: `https://your-service-name.onrender.com/health`
- Docs: `https://your-service-name.onrender.com/api/docs`
- Data: `https://your-service-name.onrender.com/api/wimbledon?year=2021`

### 2. Monitor Performance
- Check logs in Render dashboard
- Monitor Redis usage
- Set up alerts for uptime

### 3. Custom Domain (Optional)
- Add your custom domain in Render settings
- Configure DNS records

## Production Optimizations

### 1. Gunicorn Configuration
The app uses optimized Gunicorn settings:
- 4 workers for better concurrency
- Timeout settings for reliability
- Request limits to prevent memory leaks

### 2. Redis Configuration
- Connection pooling enabled
- Timeout and retry settings
- Graceful fallback when Redis is unavailable

### 3. Security Headers
- CORS configured for production
- Security headers added
- Rate limiting enabled

## Troubleshooting

### Common Issues

1. **Build Fails**:
   - Check requirements.txt for correct versions
   - Ensure all dependencies are included

2. **Redis Connection Issues**:
   - Verify REDIS_URL environment variable
   - Check Redis service status

3. **App Won't Start**:
   - Check start command syntax
   - Review application logs
   - Verify PORT environment variable

### Logs
Access logs via Render dashboard:
- Build logs: Shows installation progress
- Runtime logs: Shows application output

## Free Tier Limitations

Render's free tier includes:
- **Web Service**: 750 hours/month, sleeps after 15 min inactivity
- **Redis**: 25MB storage, 100 connections
- **Bandwidth**: 100GB/month

For production usage, consider upgrading to paid plans.

## Scaling

To handle more traffic:
1. Upgrade to paid plans
2. Increase worker count in gunicorn
3. Use Redis for session storage
4. Add CDN for static assets

## Support

For issues:
1. Check Render documentation
2. Review application logs
3. Contact Render support
4. Check community forums
