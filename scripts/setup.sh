#!/bin/bash
# GitHub Stars Manager - Unix Setup Script
echo "Setting up GitHub Stars Manager..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.9+"
    exit 1
fi

echo "Installing frontend dependencies..."
cd github-stars-manager-frontend
pnpm install --prefer-offline
cd ..

echo "Installing backend dependencies..."
cd backend
pnpm install --prefer-offline
cd ..

echo "Installing Python dependencies..."
cd services
pip3 install -r requirements.txt
cd ..

echo "Setup complete!"
