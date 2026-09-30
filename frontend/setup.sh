#!/usr/bin/env bash
# EduSight Frontend — Setup & Dev Script
# Run this from /home/dinesh/EduSight/frontend/

set -e

echo "=============================="
echo " EduSight Frontend Setup"
echo "=============================="

# Check node/npm
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js not found. Install from https://nodejs.org"
  exit 1
fi

NODE_VER=$(node --version)
NPM_VER=$(npm --version)
echo "Node: $NODE_VER  |  npm: $NPM_VER"

# Install dependencies
echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "Dependencies installed successfully!"
echo ""
echo "Starting dev server at http://localhost:5173 ..."
npm run dev
