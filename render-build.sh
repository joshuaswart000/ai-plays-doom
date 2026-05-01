#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Update pip
pip install --upgrade pip

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Ensure vizdoom has a place to live
# Render doesn't let us use 'apt-get', but we can force 
# a headless-friendly install of opencv if it's missing.
pip install opencv-python-headless
