#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create the database
echo "Creating the database..."
sqlite3 chat_group.db < init.sql

echo "Deployment complete!"
