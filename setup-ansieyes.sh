#!/bin/bash

##############################################################################
# Ansieyes One-Click Setup Script
# Sets up everything needed to run Ansieyes with AI-Issue-Triage
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

##############################################################################
# Helper Functions
##############################################################################

print_header() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "$1"
    echo "============================================================"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

##############################################################################
# Main Setup Functions
##############################################################################

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_deps=0
    local needs_install=()
    
    # Check Python
    if check_command python3; then
        python_version=$(python3 --version)
        print_info "Python version: $python_version"
    else
        print_error "python3 is required but not installed"
        needs_install+=("python3")
        missing_deps=1
    fi
    
    # Check pip
    if check_command pip3; then
        print_success "pip3 is installed"
        pip_version=$(pip3 --version)
        print_info "pip version: $pip_version"
    elif check_command pip; then
        print_success "pip is installed"
        pip_version=$(pip --version)
        print_info "pip version: $pip_version"
    else
        print_error "pip is required but not installed"
        needs_install+=("python3-pip")
        missing_deps=1
    fi
    
    # Check git
    if check_command git; then
        print_success "git is installed"
    else
        print_error "git is required but not installed"
        needs_install+=("git")
        missing_deps=1
    fi
    
    # Check Node.js
    if check_command node; then
        node_version=$(node --version)
        print_info "Node.js version: $node_version"
    else
        print_warning "Node.js is not installed - will attempt to install"
        needs_install+=("nodejs")
    fi
    
    # Check npm
    if check_command npm; then
        npm_version=$(npm --version)
        print_info "npm version: $npm_version"
    else
        print_warning "npm is not installed - will install with Node.js"
        if [[ ! " ${needs_install[@]} " =~ " nodejs " ]]; then
            needs_install+=("npm")
        fi
    fi
    
    if [ $missing_deps -eq 1 ]; then
        echo
        print_error "Some critical prerequisites are missing!"
        echo
        print_warning "Would you like to install them automatically? (requires sudo)"
        echo "Missing packages: ${needs_install[*]}"
        echo
        read -p "Install missing packages? (y/n): " install_deps
        
        if [[ $install_deps == "y" || $install_deps == "Y" ]]; then
            install_system_dependencies "${needs_install[@]}"
        else
            echo
            print_info "Manual installation commands:"
            echo
            if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                if command -v apt-get &> /dev/null; then
                    echo "  sudo apt update"
                    echo "  sudo apt install -y ${needs_install[*]}"
                elif command -v yum &> /dev/null; then
                    echo "  sudo yum install -y ${needs_install[*]}"
                fi
            elif [[ "$OSTYPE" == "darwin"* ]]; then
                echo "  brew install ${needs_install[*]}"
            fi
            echo
            exit 1
        fi
    fi
    
    print_success "All critical prerequisites are installed"
    echo
}

install_system_dependencies() {
    local packages=("$@")
    
    print_header "Installing System Dependencies"
    
    print_info "Installing: ${packages[*]}"
    echo
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            print_info "Using apt (Debian/Ubuntu)..."
            sudo apt update
            if sudo apt install -y "${packages[@]}"; then
                print_success "Packages installed successfully"
                
                # Refresh PATH to include newly installed binaries
                export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
                hash -r  # Clear bash's command cache
                
                # Verify critical commands are now available
                if [[ " ${packages[@]} " =~ " nodejs " ]] || [[ " ${packages[@]} " =~ " npm " ]]; then
                    if ! command -v npm &> /dev/null; then
                        print_warning "npm not immediately available, sourcing profile..."
                        source /etc/profile 2>/dev/null || true
                        source ~/.bashrc 2>/dev/null || true
                        export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
                    fi
                fi
            else
                print_error "Failed to install some packages"
                exit 1
            fi
        elif command -v yum &> /dev/null; then
            print_info "Using yum (RHEL/CentOS/Amazon Linux)..."
            if sudo yum install -y "${packages[@]}"; then
                print_success "Packages installed successfully"
                
                # Refresh PATH
                export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
                hash -r
                
                # Verify npm
                if [[ " ${packages[@]} " =~ " nodejs " ]] || [[ " ${packages[@]} " =~ " npm " ]]; then
                    if ! command -v npm &> /dev/null; then
                        print_warning "npm not immediately available, sourcing profile..."
                        source /etc/profile 2>/dev/null || true
                        source ~/.bashrc 2>/dev/null || true
                        export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
                    fi
                fi
            else
                print_error "Failed to install some packages"
                exit 1
            fi
        else
            print_error "Unsupported package manager"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            print_info "Using Homebrew (macOS)..."
            if brew install "${packages[@]}"; then
                print_success "Packages installed successfully"
                
                # Refresh PATH for Homebrew
                eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null || true
                hash -r
            else
                print_error "Failed to install some packages"
                exit 1
            fi
        else
            print_error "Homebrew not found. Please install from: https://brew.sh"
            exit 1
        fi
    else
        print_error "Unsupported operating system"
        exit 1
    fi
    
    # Final verification
    print_info "Verifying installations..."
    for pkg in "${packages[@]}"; do
        case "$pkg" in
            nodejs)
                if command -v node &> /dev/null; then
                    print_success "node: $(node --version)"
                else
                    print_error "node command not found after installation"
                fi
                ;;
            npm)
                if command -v npm &> /dev/null; then
                    print_success "npm: $(npm --version)"
                else
                    print_error "npm command not found after installation"
                    print_info "You may need to restart your terminal or run: source ~/.bashrc"
                fi
                ;;
            python3-pip)
                if command -v pip3 &> /dev/null; then
                    print_success "pip3: $(pip3 --version | cut -d' ' -f2)"
                else
                    print_error "pip3 command not found after installation"
                fi
                ;;
        esac
    done
    
    echo
}

install_nodejs() {
    print_header "Installing Node.js and npm"
    
    # Check if Node.js is installed and version
    if command -v node &> /dev/null; then
        node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -ge 20 ]; then
            print_info "Node.js $(node --version) already installed (version 20+) ✓"
            return 0
        else
            print_warning "Node.js $(node --version) is installed but Repomix requires version 20+"
            print_info "Upgrading to Node.js 20 LTS..."
        fi
    fi
    
    echo "Detecting OS..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            print_info "Installing Node.js 20 via Homebrew..."
            brew install node@20 || brew upgrade node
        else
            print_error "Homebrew not found. Please install Node.js 20+ manually:"
            print_info "Visit: https://nodejs.org/"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - use NodeSource for latest Node.js 20 LTS
        print_info "Installing Node.js 20 LTS via NodeSource..."
        
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            # Remove old Node.js if present
            sudo apt-get remove -y nodejs npm 2>/dev/null || true
            
            # Add NodeSource repository for Node.js 20.x
            print_info "Adding NodeSource repository..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            
            # Install Node.js 20
            print_info "Installing Node.js 20..."
            sudo apt-get install -y nodejs
            
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS/Amazon Linux
            sudo yum remove -y nodejs npm 2>/dev/null || true
            
            # Add NodeSource repository
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
            
            # Install Node.js 20
            sudo yum install -y nodejs
        else
            print_error "Package manager not supported. Please install Node.js 20+ manually:"
            print_info "Visit: https://nodejs.org/"
            exit 1
        fi
        
        # Verify installation
        if command -v node &> /dev/null; then
            node_version=$(node --version)
            print_success "Node.js $node_version installed successfully"
        else
            print_error "Node.js installation failed"
            exit 1
        fi
    else
        print_error "OS not supported. Please install Node.js 20+ manually:"
        print_info "Visit: https://nodejs.org/"
        exit 1
    fi
    
    echo
}

install_repomix() {
    print_header "Installing Repomix"
    
    if command -v repomix &> /dev/null; then
        print_info "Repomix already installed, skipping..."
        return 0
    fi
    
    # Verify npm is available
    if ! command -v npm &> /dev/null; then
        print_error "npm command not found!"
        print_warning "npm was installed but is not available in the current shell"
        echo
        print_info "Please run the following command and then re-run this script:"
        echo "  source ~/.bashrc"
        echo "  # OR restart your terminal"
        echo
        exit 1
    fi
    
    print_info "Installing repomix globally..."
    if npm install -g repomix; then
        print_success "Repomix installed successfully"
        
        if command -v repomix &> /dev/null; then
            repomix_version=$(repomix --version)
            print_info "Repomix version: $repomix_version"
        else
            print_warning "repomix installed but not in PATH"
            print_info "You may need to add npm global bin to PATH"
            print_info "Run: export PATH=\"\$(npm config get prefix)/bin:\$PATH\""
        fi
    else
        print_error "Failed to install repomix"
        print_info "Try manually: npm install -g repomix"
        exit 1
    fi
    
    echo
}

setup_ai_issue_triage() {
    print_header "Setting up AI-Issue-Triage"
    
    # Determine appropriate default based on actual user (not root if using sudo)
    if [ -n "$SUDO_USER" ]; then
        DEFAULT_USER="$SUDO_USER"
        DEFAULT_HOME=$(eval echo "~$SUDO_USER")
    else
        DEFAULT_USER="$(whoami)"
        DEFAULT_HOME="$HOME"
    fi
    
    echo "Where do you want to install AI-Issue-Triage?"
    echo "Press Enter for default: $DEFAULT_HOME/AI-Issue-Triage"
    echo "(Note: Ansieyes service will run as user: $DEFAULT_USER)"
    read -p "Path: " ai_triage_path
    
    if [ -z "$ai_triage_path" ]; then
        ai_triage_path="$DEFAULT_HOME/AI-Issue-Triage"
    fi
    
    # Expand ~ to home directory
    ai_triage_path="${ai_triage_path/#\~/$DEFAULT_HOME}"
    
    if [ -d "$ai_triage_path" ]; then
        print_warning "Directory already exists: $ai_triage_path"
        read -p "Do you want to use this existing installation? (y/n): " use_existing
        if [[ $use_existing == "y" || $use_existing == "Y" ]]; then
            export AI_TRIAGE_PATH="$ai_triage_path"
            print_success "Using existing AI-Issue-Triage installation"
            return 0
        else
            print_info "Removing existing directory..."
            rm -rf "$ai_triage_path"
        fi
    fi
    
    print_info "Cloning AI-Issue-Triage repository..."
    git clone https://github.com/shvenkat-rh/AI-Issue-Triage.git "$ai_triage_path"
    
    # Fix ownership if running as sudo
    if [ -n "$SUDO_USER" ]; then
        print_info "Setting ownership to $SUDO_USER..."
        chown -R "$SUDO_USER:$SUDO_USER" "$ai_triage_path"
    fi
    
    print_info "Checking out feature/pr-analyzer branch..."
    cd "$ai_triage_path"
    git checkout feature/pr-analyzer || git checkout main
    
    print_info "Installing AI-Issue-Triage dependencies..."
    
    # Add .local/bin to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Check if we're in an externally-managed environment
    if python3 -m pip --version &>/dev/null; then
        echo ""
        
        # Try regular pip install first (without --ignore-installed for better performance)
        # Use a temporary file to capture stderr while showing stdout
        temp_err=$(mktemp)
        if pip3 install --no-warn-script-location -r requirements.txt 2> "$temp_err"; then
            rm -f "$temp_err"
            print_success "AI-Issue-Triage dependencies installed"
        else
            # Check what error occurred
            error_output=$(cat "$temp_err")
            rm -f "$temp_err"
            
            if echo "$error_output" | grep -q "externally-managed-environment"; then
                print_warning "Externally-managed Python environment detected"
                print_info "Retrying with --break-system-packages flag"
                echo ""
                
                if pip3 install --break-system-packages --no-warn-script-location -r requirements.txt; then
                    print_success "AI-Issue-Triage dependencies installed"
                else
                    print_error "Failed to install AI-Issue-Triage dependencies"
                    print_info "Try manually: cd $ai_triage_path && pip3 install --break-system-packages -r requirements.txt"
                    exit 1
                fi
            elif echo "$error_output" | grep -q "Cannot uninstall"; then
                print_warning "Conflict with system packages detected (Debian-managed packages)"
                print_info "Retrying with --break-system-packages and --ignore-installed flags"
                echo ""
                
                if pip3 install --break-system-packages --ignore-installed --no-warn-script-location -r requirements.txt; then
                    print_success "AI-Issue-Triage dependencies installed"
                else
                    print_error "Failed to install AI-Issue-Triage dependencies"
                    exit 1
                fi
            else
                print_error "Failed to install AI-Issue-Triage dependencies"
                echo "$error_output"
                print_info "Try manually: cd $ai_triage_path && pip3 install -r requirements.txt"
                exit 1
            fi
        fi
    else
        print_error "pip not available"
        exit 1
    fi
    
    export AI_TRIAGE_PATH="$ai_triage_path"
    print_success "AI-Issue-Triage installed at: $ai_triage_path"
    
    cd "$SCRIPT_DIR"
    echo
}

install_ansieyes_dependencies() {
    print_header "Installing Ansieyes Dependencies"
    
    cd "$SCRIPT_DIR"
    
    # Add .local/bin to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    
    print_info "Installing Python packages from requirements.txt..."
    print_info "Note: Many dependencies already installed by AI-Issue-Triage will be skipped"
    
    # Try pip3 first, then pip
    if command -v pip3 &> /dev/null; then
        print_info "Using pip3..."
        echo ""
        
        # First, try a simple install without --ignore-installed (faster, avoids reinstalling shared deps)
        # Use a temporary file to capture stderr while showing stdout
        temp_err=$(mktemp)
        if pip3 install --no-warn-script-location -r requirements.txt 2> "$temp_err"; then
            rm -f "$temp_err"
            print_success "Dependencies installed successfully"
        else
            # Check what error occurred
            error_output=$(cat "$temp_err")
            rm -f "$temp_err"
            
            if echo "$error_output" | grep -q "externally-managed-environment"; then
                print_warning "Externally-managed Python environment detected"
                print_info "Retrying with --break-system-packages flag"
                echo ""
                
                if pip3 install --break-system-packages --no-warn-script-location -r requirements.txt; then
                    print_success "Dependencies installed successfully"
                else
                    print_error "Failed to install dependencies"
                    print_info "Try manually: pip3 install --break-system-packages -r requirements.txt"
                    exit 1
                fi
            elif echo "$error_output" | grep -q "Cannot uninstall"; then
                print_warning "Conflict with system packages detected"
                print_info "Retrying with --break-system-packages and --ignore-installed flags"
                echo ""
                
                if pip3 install --break-system-packages --ignore-installed --no-warn-script-location -r requirements.txt; then
                    print_success "Dependencies installed successfully"
                else
                    print_error "Failed to install dependencies"
                    exit 1
                fi
            else
                print_error "Failed to install dependencies"
                echo "$error_output"
                print_info "Try manually: pip3 install -r requirements.txt"
                exit 1
            fi
        fi
    elif command -v pip &> /dev/null; then
        print_info "Using pip..."
        if pip install --no-warn-script-location -r requirements.txt; then
            print_success "Dependencies installed successfully"
        else
            print_error "Failed to install dependencies"
            print_info "Try manually: pip install -r requirements.txt"
            exit 1
        fi
    else
        print_error "Neither pip nor pip3 found"
        print_info "Please install pip first: sudo apt install python3-pip"
        exit 1
    fi
    
    # Ensure .local/bin is in PATH permanently
    add_local_bin_to_path
    
    echo
}

add_local_bin_to_path() {
    print_info "Ensuring $HOME/.local/bin is in PATH..."
    
    local bashrc="$HOME/.bashrc"
    local profile="$HOME/.profile"
    local path_line='export PATH="$HOME/.local/bin:$PATH"'
    
    # Check if already in .bashrc
    if [ -f "$bashrc" ]; then
        if ! grep -q '.local/bin' "$bashrc"; then
            echo "" >> "$bashrc"
            echo "# Added by Ansieyes setup" >> "$bashrc"
            echo "$path_line" >> "$bashrc"
            print_success "Added .local/bin to PATH in .bashrc"
        else
            print_info ".local/bin already in .bashrc PATH"
        fi
    fi
    
    # Also add to .profile for non-interactive shells
    if [ -f "$profile" ]; then
        if ! grep -q '.local/bin' "$profile"; then
            echo "" >> "$profile"
            echo "# Added by Ansieyes setup" >> "$profile"
            echo "$path_line" >> "$profile"
            print_success "Added .local/bin to PATH in .profile"
        fi
    fi
    
    # Export for current session
    export PATH="$HOME/.local/bin:$PATH"
}

configure_environment() {
    print_header "Configuring Environment"
    
    echo
    print_info "You will need the following credentials:"
    echo "  ✓ Gemini API key (for AI features)"
    echo "  ✓ GitHub App ID, private key, webhook secret"
    echo "  ✗ AWS credentials are NOT needed"
    echo
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/n): " overwrite
        if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
            print_info "Keeping existing .env file"
            return 0
        fi
    fi
    
    print_info "Creating .env file..."
    
    # Gemini API Key
    echo
    print_info "Get your Gemini API key from: https://makersuite.google.com/app/apikey"
    read -p "Enter your Gemini API key: " gemini_api_key
    
    # GitHub App ID
    echo
    print_info "You'll need to create a GitHub App first if you haven't already."
    print_info "Follow the guide at: https://github.com/settings/apps"
    read -p "Enter your GitHub App ID: " github_app_id
    
    # GitHub Private Key Path
    echo
    read -p "Enter the full path to your GitHub App private key (.pem file): " github_private_key_path
    github_private_key_path="${github_private_key_path/#\~/$HOME}"
    
    if [ ! -f "$github_private_key_path" ]; then
        print_error "Private key file not found: $github_private_key_path"
        print_warning "Please make sure the file exists and try again"
    fi
    
    # Webhook Secret
    echo
    read -p "Enter your GitHub webhook secret: " github_webhook_secret
    
    # Port and Host
    echo
    read -p "Enter port number (default 3000): " port
    port=${port:-3000}
    
    read -p "Enter host (default 0.0.0.0): " host
    host=${host:-0.0.0.0}
    
    # Create .env file
    cat > .env << EOF
# Gemini API Configuration
GEMINI_API_KEY=$gemini_api_key

# GitHub App Configuration
GITHUB_APP_ID=$github_app_id
GITHUB_PRIVATE_KEY_PATH=$github_private_key_path
GITHUB_WEBHOOK_SECRET=$github_webhook_secret

# AI-Issue-Triage Configuration
AI_TRIAGE_PATH=$AI_TRIAGE_PATH

# Server Configuration
PORT=$port
HOST=$host
EOF
    
    print_success ".env file created successfully"
    echo
}

setup_github_app_instructions() {
    print_header "GitHub App Setup Instructions"
    
    echo
    print_info "If you haven't created a GitHub App yet, follow these steps:"
    echo
    echo "1. Go to: https://github.com/settings/apps"
    echo "2. Click 'New GitHub App'"
    echo
    echo "3. Basic Information:"
    echo "   - Name: ansieyes-bot (or your choice)"
    echo "   - Homepage URL: https://github.com/your-username/Ansieyes"
    echo "   - Webhook URL: (use ngrok URL for testing)"
    echo "   - Webhook secret: (use a strong random string)"
    echo
    echo "4. Permissions (Repository):"
    echo "   - Contents: Read-only"
    echo "   - Issues: Read and write ✓"
    echo "   - Pull requests: Read and write ✓"
    echo "   - Actions: Read-only"
    echo
    echo "5. Subscribe to events:"
    echo "   ☑ Issue comment"
    echo "   ☑ Pull request"
    echo "   ☑ Workflow run"
    echo
    echo "6. After creation:"
    echo "   - Save the App ID"
    echo "   - Generate and download private key (.pem file)"
    echo "   - Install the app on your repositories"
    echo
    
    read -p "Press Enter when you have completed the GitHub App setup..."
    echo
}

test_setup() {
    print_header "Testing Setup"
    
    print_info "Verifying Python dependencies..."
    python3 -c "import flask; print('Flask:', flask.__version__)"
    python3 -c "import google.generativeai as genai; print('Gemini: OK')"
    python3 -c "from github import Github; print('PyGithub: OK')"
    python3 -c "import pydantic; print('Pydantic:', pydantic.__version__)"
    
    print_success "All Python dependencies verified"
    
    print_info "Verifying repomix..."
    repomix --version
    
    print_info "Verifying AI-Issue-Triage..."
    if [ -d "$AI_TRIAGE_PATH" ]; then
        print_success "AI-Issue-Triage found at: $AI_TRIAGE_PATH"
    else
        print_error "AI-Issue-Triage not found at: $AI_TRIAGE_PATH"
        return 1
    fi
    
    print_success "All tests passed!"
    echo
}

start_with_ngrok() {
    print_header "Starting Ansieyes with ngrok"
    
    if ! command -v ngrok &> /dev/null; then
        print_warning "ngrok is not installed"
        print_info "Install ngrok from: https://ngrok.com/download"
        print_info "Or on macOS: brew install ngrok"
        echo
        read -p "Do you want to start without ngrok? (y/n): " start_anyway
        if [[ $start_anyway != "y" && $start_anyway != "Y" ]]; then
            return 0
        fi
    fi
    
    echo
    print_info "To start Ansieyes:"
    echo
    echo "Terminal 1:"
    echo "  cd $SCRIPT_DIR"
    echo "  python3 app.py"
    echo
    echo "Terminal 2 (if using ngrok):"
    echo "  ngrok http 3000"
    echo "  Then update your GitHub App webhook URL with the ngrok URL"
    echo
    
    read -p "Do you want to start Ansieyes now? (y/n): " start_now
    if [[ $start_now == "y" || $start_now == "Y" ]]; then
        print_info "Starting Ansieyes..."
        python3 app.py
    fi
}

detect_ec2() {
    # Check if running on EC2
    if [ -f /sys/hypervisor/uuid ] && [ `head -c 3 /sys/hypervisor/uuid` == ec2 ]; then
        return 0
    elif curl -s -m 1 http://169.254.169.254/latest/meta-data/ &> /dev/null; then
        return 0
    else
        return 1
    fi
}

get_ec2_public_ip() {
    # Use IMDSv2 (requires session token)
    local token=$(curl -X PUT -s -f --connect-timeout 2 "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
    if [ -n "$token" ]; then
        curl -s -f --connect-timeout 2 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null
    else
        # Fallback to IMDSv1 if v2 fails
        curl -s -f --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null
    fi
}

get_ec2_public_dns() {
    # Use IMDSv2 (requires session token)
    local token=$(curl -X PUT -s -f --connect-timeout 2 "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)
    if [ -n "$token" ]; then
        curl -s -f --connect-timeout 2 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/public-hostname 2>/dev/null
    else
        # Fallback to IMDSv1 if v2 fails
        curl -s -f --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-hostname 2>/dev/null
    fi
}

setup_systemd_service() {
    print_header "Setting up Systemd Service"
    
    local service_file="/etc/systemd/system/ansieyes.service"
    local work_dir="$SCRIPT_DIR"
    # Use actual user, not root if running with sudo
    local user="${SUDO_USER:-$USER}"
    
    print_info "Creating systemd service file..."
    
    sudo tee $service_file > /dev/null << EOF
[Unit]
Description=Ansieyes GitHub Bot
After=network.target

[Service]
Type=simple
User=$user
WorkingDirectory=$work_dir
Environment="PATH=/home/$user/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="NODE_PATH=/usr/local/lib/node_modules"
EnvironmentFile=$work_dir/.env
ExecStart=/usr/bin/python3 $work_dir/app.py
Restart=always
RestartSec=10
StandardOutput=append:$work_dir/ansieyes.log
StandardError=append:$work_dir/ansieyes.log

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Systemd service created"
    
    print_info "Enabling and starting service..."
    sudo systemctl daemon-reload
    sudo systemctl enable ansieyes
    sudo systemctl start ansieyes
    
    sleep 2
    
    if sudo systemctl is-active --quiet ansieyes; then
        print_success "Ansieyes service is running!"
        print_info "Check logs: journalctl -u ansieyes -f"
    else
        print_error "Service failed to start. Check logs: journalctl -u ansieyes -xe"
    fi
    
    echo
}

setup_nginx_ssl() {
    print_header "Setting up Nginx with SSL"
    
    read -p "Enter your domain name (e.g., ansieyes.yourdomain.com): " domain_name
    
    if [ -z "$domain_name" ]; then
        print_warning "No domain provided, skipping nginx setup"
        return 0
    fi
    
    read -p "Enter your email for Let's Encrypt SSL: " email
    
    print_info "Installing nginx and certbot..."
    sudo apt update
    sudo apt install -y nginx certbot python3-certbot-nginx
    
    print_info "Creating nginx configuration..."
    
    sudo tee /etc/nginx/sites-available/ansieyes > /dev/null << EOF
server {
    server_name $domain_name;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/ansieyes /etc/nginx/sites-enabled/
    sudo nginx -t
    
    if [ $? -eq 0 ]; then
        sudo systemctl restart nginx
        print_success "Nginx configured successfully"
        
        print_info "Obtaining SSL certificate from Let's Encrypt..."
        sudo certbot --nginx -d $domain_name --non-interactive --agree-tos --email $email
        
        if [ $? -eq 0 ]; then
            print_success "SSL certificate obtained!"
            print_success "Your webhook URL: https://$domain_name/webhook"
        else
            print_warning "SSL setup failed. You can set it up manually later."
            print_info "Your webhook URL: http://$domain_name/webhook"
        fi
    else
        print_error "Nginx configuration test failed"
    fi
    
    echo
}

deploy_to_ec2() {
    print_header "EC2 Production Deployment"
    
    # Detect if we're on EC2
    if detect_ec2; then
        print_success "Detected EC2 environment"
        echo
        print_info "ℹ️  Note: AWS credentials are NOT required for this setup"
        print_info "The script only needs GitHub and Gemini API credentials"
        echo
        
        # Get EC2 info
        public_ip=$(get_ec2_public_ip)
        public_dns=$(get_ec2_public_dns)
        
        # Validate that we got the metadata
        if [ -z "$public_ip" ] || [[ "$public_ip" == *"401"* ]] || [[ "$public_ip" == *"Unauthorized"* ]]; then
            print_warning "Could not fetch EC2 public IP from metadata service"
            print_info "This may happen if IMDSv2 is required or metadata service is restricted"
            read -p "Please enter your EC2 public IP manually: " public_ip
        else
            print_info "EC2 Public IP: $public_ip"
        fi
        
        if [ -z "$public_dns" ] || [[ "$public_dns" == *"401"* ]] || [[ "$public_dns" == *"Unauthorized"* ]]; then
            print_warning "Could not fetch EC2 public DNS from metadata service"
            read -p "Please enter your EC2 public DNS manually (or press Enter to skip): " public_dns
        else
            print_info "EC2 Public DNS: $public_dns"
        fi
        echo
        
        # Webhook URL options
        print_info "Webhook URL Options:"
        echo "1) http://$public_ip:3000/webhook (Direct IP)"
        echo "2) http://$public_dns:3000/webhook (Public DNS)"
        echo "3) Custom domain with SSL (Recommended)"
        echo
        
        read -p "Choose option (1-3): " url_choice
        
        case $url_choice in
            1)
                WEBHOOK_URL="http://$public_ip:3000/webhook"
                ;;
            2)
                WEBHOOK_URL="http://$public_dns:3000/webhook"
                ;;
            3)
                read -p "Do you want to setup nginx with SSL now? (y/n): " setup_ssl
                if [[ $setup_ssl == "y" || $setup_ssl == "Y" ]]; then
                    setup_nginx_ssl
                    return 0
                else
                    print_warning "You can setup nginx later with: sudo apt install nginx certbot python3-certbot-nginx"
                    WEBHOOK_URL="http://$public_ip:3000/webhook"
                fi
                ;;
            *)
                WEBHOOK_URL="http://$public_ip:3000/webhook"
                ;;
        esac
        
        print_success "Webhook URL: $WEBHOOK_URL"
        
        # Setup systemd service
        read -p "Do you want to setup Ansieyes as a systemd service? (y/n): " setup_service
        if [[ $setup_service == "y" || $setup_service == "Y" ]]; then
            setup_systemd_service
        fi
        
        # Security Group instructions
        print_header "Security Group Configuration"
        print_warning "IMPORTANT: Configure your EC2 Security Group"
        echo
        echo "AWS Console → EC2 → Security Groups → Your Instance Security Group"
        echo
        echo "Add these inbound rules:"
        if [[ $url_choice == "3" ]]; then
            echo "  - Type: HTTP, Port: 80, Source: 0.0.0.0/0"
            echo "  - Type: HTTPS, Port: 443, Source: 0.0.0.0/0"
        else
            echo "  - Type: Custom TCP, Port: 3000, Source: 0.0.0.0/0"
            echo "  - (Or restrict to GitHub webhook IPs for better security)"
        fi
        echo
        
        print_success "EC2 deployment configuration complete!"
        echo
        print_info "Next steps:"
        echo "1. Update GitHub App webhook URL to: $WEBHOOK_URL"
        echo "2. Configure Security Group as shown above"
        echo "3. Test with: \ansieyes_triage or \ansieyes_prreview"
        
    else
        print_warning "Not running on EC2"
        print_info "For EC2 deployment:"
        echo "1. SSH into your EC2 instance"
        echo "2. Run this script there: ./setup-ansieyes.sh"
        echo "3. Choose option 3 (EC2 Production Deployment)"
        echo
        print_info "Alternative: See docs/AWS_DEPLOYMENT.md for manual setup"
    fi
    
    echo
}

print_completion_message() {
    print_header "Setup Complete! 🎉"
    
    echo
    print_success "Ansieyes is ready to use!"
    echo
    echo "Quick Start:"
    echo "  1. Start the bot: python3 app.py"
    echo "  2. Setup ngrok: ngrok http 3000"
    echo "  3. Update GitHub App webhook URL"
    echo "  4. Test with: \ansieyes_triage (on issue) or \ansieyes_prreview (on PR)"
    echo
    echo "Documentation:"
    echo "  - Complete Guide: COMPLETE_SETUP_GUIDE.md"
    echo "  - Configuration: triage.config.example.json"
    echo
    echo "Commands:"
    echo "  - \ansieyes_triage    - Issue triage (exact match only)"
    echo "  - \ansieyes_prreview  - PR review (exact match only)"
    echo
    print_info "Remember: Commands must be exact with no extra text!"
    echo
}

##############################################################################
# Main Menu
##############################################################################

show_menu() {
    print_header "Ansieyes Setup Script"
    
    # Detect environment
    local is_ec2=false
    if detect_ec2; then
        is_ec2=true
        print_success "Detected EC2 environment"
        echo
    fi
    
    echo "Choose your setup option:"
    echo
    echo "1) Complete Setup (Recommended)"
    echo "   - Install all dependencies"
    echo "   - Setup AI-Issue-Triage"
    echo "   - Configure environment"
    echo "   - Test setup"
    if $is_ec2; then
        echo "   - EC2 production deployment"
    fi
    echo
    echo "2) Quick Setup (Dependencies already installed)"
    echo "   - Configure environment only"
    echo "   - Test setup"
    echo
    echo "3) EC2 Production Deployment"
    echo "   - Setup systemd service"
    echo "   - Configure nginx + SSL (optional)"
    echo "   - Get webhook URL"
    echo
    echo "4) Test Existing Setup"
    echo "   - Verify installation"
    echo
    echo "5) Exit"
    echo
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            complete_setup
            ;;
        2)
            quick_setup
            ;;
        3)
            deploy_to_ec2
            ;;
        4)
            test_setup
            ;;
        5)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            show_menu
            ;;
    esac
}

complete_setup() {
    check_prerequisites
    install_nodejs
    install_repomix
    setup_ai_issue_triage
    install_ansieyes_dependencies
    setup_github_app_instructions
    configure_environment
    test_setup
    
    # Check if on EC2 for production deployment
    if detect_ec2; then
        echo
        read -p "Detected EC2. Setup for production now? (y/n): " setup_prod
        if [[ $setup_prod == "y" || $setup_prod == "Y" ]]; then
            deploy_to_ec2
        else
            start_with_ngrok
        fi
    else
        start_with_ngrok
    fi
    
    print_completion_message
}

quick_setup() {
    configure_environment
    test_setup
    start_with_ngrok
    print_completion_message
}

##############################################################################
# Main Execution
##############################################################################

main() {
    clear
    
    print_header "Welcome to Ansieyes Setup!"
    
    echo "This script will help you set up Ansieyes with AI-powered"
    echo "PR review and issue triage capabilities."
    echo
    print_warning "What you need:"
    echo "  ✓ GitHub account with admin access"
    echo "  ✓ Gemini API key (https://makersuite.google.com/app/apikey)"
    echo "  ✓ For EC2: SSH access to your instance"
    echo
    print_info "What you DON'T need:"
    echo "  ✗ AWS credentials (not required for EC2 setup)"
    echo "  ✗ AWS CLI (not needed)"
    echo
    print_info "The script runs locally and only installs software."
    echo
    read -p "Press Enter to continue..."
    
    show_menu
}

# Run main function
main


