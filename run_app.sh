#!/bin/bash

# Load environment variables from .env file (if it exists)
ENV_FILE="/usr/local/hailo/resources/.env"
if [ -f "$ENV_FILE" ]; then
    # Export variables from .env file (skip comments and empty lines)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        # Export both original case and uppercase versions
        export "$key=$value"
        upper_key=$(echo "$key" | tr '[:lower:]' '[:upper:]')
        export "$upper_key=$value"
    done < "$ENV_FILE"
    echo "Environment variables loaded from $ENV_FILE"
fi

# Activate our custom venv with system packages
source pocket-ai/bin/activate
echo "Virtual environment 'pocket-ai' activated"

# Cleanup any existing process on port 8000
echo "Ensuring port 8000 is free..."
fuser -k 8000/tcp 2>/dev/null || true

# Run app.py from current directory
python app.py "$@"
