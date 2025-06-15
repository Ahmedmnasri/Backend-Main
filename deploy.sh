#!/bin/bash

# Railway Deployment Script for Digital Field Inspection Backend
echo "🚀 Starting Railway deployment process..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed. Installing now..."
    curl -fsSL https://railway.app/install.sh | sh
    echo "✅ Railway CLI installed successfully"
fi

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo "❌ You are not logged in to Railway"
    echo "Please run: railway login"
    echo "Then run this script again"
    exit 1
fi

echo "✅ Railway CLI is ready"

# Check if this is a Railway project
if [ ! -f "railway.toml" ]; then
    echo "❌ railway.toml not found. This doesn't appear to be a Railway project."
    echo "Please run: railway init"
    exit 1
fi

echo "✅ Railway configuration found"

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo "🌐 Your application should be available at your Railway domain"
echo "🔍 Check deployment status: railway status"
echo "📋 View logs: railway logs"
