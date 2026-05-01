#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Render doesn't allow sudo, but vizdoom wheels often 
# bundle what they need. If it fails, we will use a 
# specialized "headless" version of the library.
