#!/bin/bash
# Optional local build helper. Vercel's @vercel/python builder installs
# requirements.txt automatically; this script is for local use only.
set -e
echo "Installing Python dependencies..."
pip install -r requirements.txt
mkdir -p static/uploads
echo "Build complete."
