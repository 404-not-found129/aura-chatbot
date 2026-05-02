#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting installation for Aura Chatbot..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Create a virtual environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --quiet --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install --quiet -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi

# Setup .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        echo "IMPORTANT: Please update the .env file with your actual API keys."
    fi
else
    echo ".env file already exists."
fi

# Create global command
echo "Setting up global 'aura' command..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

PROJECT_DIR="$(pwd)"

cat << EOF > "$BIN_DIR/aura"
#!/bin/bash
# Wrapper to run aura chatbot
cd "$PROJECT_DIR" || exit 1
"venv/bin/python" "src/aura.py" "\$@"
EOF

chmod +x "$BIN_DIR/aura"
echo "Created 'aura' command at $BIN_DIR/aura"

echo ""
echo "================================================================="
echo "Installation complete!"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "WARNING: $BIN_DIR is not in your PATH."
    echo "Add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your ~/.bashrc or ~/.zshrc."
    echo "After that, you can start the chatbot from anywhere by typing:"
    echo "  aura"
else
    echo "You can now start the chatbot from anywhere by typing:"
    echo "  aura"
fi
echo "================================================================="
