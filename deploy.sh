#!/bin/bash
# Quick deployment script for Render

echo "🚀 Preparing Wimbledon API for Render deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing Git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "📁 Adding files to Git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Prepare for Render deployment with Redis caching"

# Check if remote exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️  No Git remote found. Please add your GitHub repository:"
    echo "   git remote add origin https://github.com/yourusername/your-repo.git"
    echo "   git push -u origin main"
else
    echo "⬆️  Pushing to GitHub..."
    git push origin main
    echo ""
    echo "✅ Code pushed to GitHub!"
    echo ""
    echo "🌐 Next steps:"
    echo "1. Go to https://render.com"
    echo "2. Sign in and click 'New' → 'Blueprint'"
    echo "3. Connect your GitHub repository"
    echo "4. Render will detect render.yaml and create:"
    echo "   - Redis service (wimbledon-redis)"
    echo "   - Web service (wimbledon-api)"
    echo "5. Click 'Apply' to deploy"
    echo ""
    echo "📊 Your API will be available at:"
    echo "   https://wimbledon-api.onrender.com"
fi
