#!/bin/bash

# ============================================
# AI Job Source Agent - Demo Script
# ============================================
# This script helps you run a clean, controlled demo.
# It pauses after each major step so you can explain.

set -e

echo "=============================================="
echo "   AI Job Source Agent - Interactive Demo"
echo "=============================================="
echo ""
echo "This demo will showcase the agent's capabilities."
echo ""

read -p "Press Enter to begin the demo..."

# --------------------------------------------
# Step 1: Demo with a LinkedIn Job Listing
# --------------------------------------------
echo ""
echo ">>> STEP 1: Running agent on a LinkedIn JOB LISTING page (mock mode)"
echo ""
python main.py --linkedin-url "https://www.linkedin.com/jobs/view/1234567890" --mock

echo ""
read -p "Continue to next demo? (Y/n): " choice
if [[ "$choice" =~ ^[Nn]$ ]]; then
    echo "Demo ended by user."
    exit 0
fi

# --------------------------------------------
# Step 2: Demo with a LinkedIn Company Page
# --------------------------------------------
echo ""
echo ">>> STEP 2: Running agent on a LinkedIn COMPANY PAGE (mock mode)"
echo ""
python main.py --linkedin-url "https://www.linkedin.com/company/stripe" --mock

echo ""
read -p "Continue to show tests? (Y/n): " choice
if [[ "$choice" =~ ^[Nn]$ ]]; then
    echo "Demo ended by user."
    exit 0
fi

# --------------------------------------------
# Step 3: Show that tests are passing
# --------------------------------------------
echo ""
echo ">>> STEP 3: Running test suite to show code quality"
echo ""
pytest tests/ -q

echo ""
echo "=============================================="
echo "Demo complete. All steps finished successfully."
echo "=============================================="
