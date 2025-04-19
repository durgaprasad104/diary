#!/bin/bash
set -e

# Install system dependencies
apt-get update && apt-get install -y \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
