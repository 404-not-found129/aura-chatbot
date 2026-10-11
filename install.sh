#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# One-line install (clones into $AURA_DIR, default ~/.local/share/aura-chatbot):
#   curl -fsSL https://raw.githubusercontent.com/404-not-found129/aura-chatbot/master/install.sh | bash
# When piped from curl there is no checkout yet, so fetch or update the repo and run the installer from there.
bootstrap() {
    local dir="${AURA_DIR:-$HOME/.local/share/aura-chatbot}"
    if ! command -v git &> /dev/null; then
        echo "Error: git is required. Please install git and try again."
        exit 1
    fi
    if [ -d "$dir/.git" ]; then
        echo "Updating Aura Chatbot in $dir..."
        git -C "$dir" pull -q --ff-only
    else
        echo "Downloading Aura Chatbot to $dir..."
        git clone -q --depth 1 https://github.com/404-not-found129/aura-chatbot.git "$dir"
    fi
    cd "$dir"
    exec bash ./install.sh "$@"
}
SCRIPT="${BASH_SOURCE[0]:-}"
if [ -z "$SCRIPT" ] || [ ! -f "$(dirname "$SCRIPT")/src/aura.py" ]; then
    bootstrap "$@"
fi
# Always work from the project folder, wherever the script is run from
cd "$(dirname "$SCRIPT")"

echo "Starting installation for Aura Chatbot..."

# 1. Check for Docker and install if missing
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. It is required for safe virtual machine isolation."
    echo "Attempting to install Docker automatically..."
    if command -v curl &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Add current user to docker group
        echo "Adding $USER to the docker group..."
        sudo usermod -aG docker "$USER"
        echo "Docker installed successfully! Note: You may need to restart your terminal or log out and log back in for group changes to take effect."
    else
        echo "Error: curl is required to install Docker. Please install curl or install Docker manually."
        exit 1
    fi
else
    echo "Docker is already installed."
fi

# Make sure the Docker daemon is running and this user may talk to it
DOCKER="docker"
if ! docker info &> /dev/null; then
    if command -v systemctl &> /dev/null && ! systemctl is-active --quiet docker; then
        echo "Starting the Docker service..."
        sudo systemctl enable --now docker
    fi
    if ! docker info &> /dev/null; then
        if ! id -nG "$USER" | grep -qw docker; then
            echo "Adding $USER to the docker group (takes effect after you log out and back in)..."
            sudo usermod -aG docker "$USER"
        fi
        # The new group isn't active in this shell yet, so use sudo for this install only
        DOCKER="sudo docker"
    fi
fi

# 2. Setup .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        echo "IMPORTANT: Please update the .env file with your actual API keys."
    fi
else
    echo ".env file already exists."
fi

# Ensure .env is explicitly created if .env.example didn't exist
touch .env

# 3. Build the Docker Image
echo "Building Aura Chatbot Docker image..."
$DOCKER build -t aura-chatbot .

# 4. Create global command
echo "Setting up global 'aura' command..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

PROJECT_DIR="$(pwd)"
ENV_PATH="$PROJECT_DIR/.env"

cat << EOF > "$BIN_DIR/aura"
#!/bin/bash
# Wrapper to run aura chatbot in a Docker VM

# Ensure docker daemon is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker daemon is not running or you do not have permission to access it."
    echo "If you just installed Docker, try logging out and logging back in, or run 'sudo usermod -aG docker \$USER'."
    exit 1
fi

docker run -it --rm \\
    -v "\$(pwd):/app/workspace" \\
    -v /var/run/docker.sock:/var/run/docker.sock \\
    -v "$ENV_PATH:/app/.env" \\
    -e HOST_WORKSPACE="\$(pwd)" \\
    -w /app/workspace \\
    aura-chatbot "\$@"
EOF

chmod +x "$BIN_DIR/aura"
echo "Created 'aura' command at $BIN_DIR/aura"

echo ""
echo "================================================================="
echo "Installation complete!"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "WARNING: $BIN_DIR is not in your PATH."
    # Read from the terminal, since stdin is the script itself when piped from curl
    add_path_choice=""
    read -p "Would you like to automatically add it to your PATH? (y/N): " add_path_choice < /dev/tty || true
    if [[ "$add_path_choice" =~ ^[Yy]$ ]]; then
        RC_FILE=""
        if [[ "$SHELL" == *"zsh"* ]] || [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
            RC_FILE="$HOME/.zshrc"
        elif [[ "$SHELL" == *"bash"* ]] || [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
            RC_FILE="$HOME/.bashrc"
        else
            RC_FILE="$HOME/.profile"
        fi
        
        echo -e "\n# Added by Aura Chatbot installer\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$RC_FILE"
        echo "✓ Successfully added to $RC_FILE."
        echo "Please run 'source $RC_FILE' or restart your terminal to apply the changes."
    else
        echo "Skipping. Please add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your ~/.bashrc or ~/.zshrc manually."
    fi
    echo "After that, you can start the chatbot from anywhere by typing:"
    echo "  aura"
else
    echo "You can now start the chatbot from anywhere by typing:"
    echo "  aura"
fi
echo "================================================================="
