#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# ViZDoom needs a placeholder for some system libs on Render
# If the build fails, we'll shift to a headless-precompiled wheel
