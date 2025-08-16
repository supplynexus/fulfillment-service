#!/bin/bash

# User Management Tool Launcher
# This script provides a convenient way to run the user management tool

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "User Management Tool for SupplyNexus Fulfillment Service"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  create <email> <password> [--full-name <name>]  Create a new user"
    echo "  update <email> <new_password>                   Update user password"
    echo "  list                                            List all users"
    echo "  show <email>                                    Show user details"
    echo "  delete <email>                                  Delete a user"
    echo ""
    echo "Examples:"
    echo "  $0 create admin@example.com MySecurePass123! --full-name \"Admin User\""
    echo "  $0 update admin@example.com NewSecurePass123!"
    echo "  $0 list"
    echo "  $0 show admin@example.com"
    echo "  $0 delete admin@example.com"
    echo ""
    echo "Password Requirements:"
    echo "  - At least 8 characters long"
    echo "  - Contains at least one uppercase letter"
    echo "  - Contains at least one lowercase letter"
    echo "  - Contains at least one digit"
    echo "  - Contains at least one special character"
}

# Function to check if virtual environment is activated
check_venv() {
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_warning "Virtual environment not detected"
        print_info "Attempting to activate virtual environment..."
        
        if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
            source "$PROJECT_DIR/.venv/bin/activate"
            print_success "Virtual environment activated"
        else
            print_error "Virtual environment not found at $PROJECT_DIR/.venv/"
            print_info "Please activate your virtual environment manually"
            exit 1
        fi
    else
        print_success "Virtual environment is active: $VIRTUAL_ENV"
    fi
}

# Function to check if required packages are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        exit 1
    fi
    
    # Check if required packages are installed
    python -c "import sqlalchemy, bcrypt" 2>/dev/null || {
        print_error "Required packages not found. Please install dependencies:"
        print_info "pip install -r requirements.txt"
        exit 1
    }
    
    print_success "Dependencies check passed"
}

# Function to validate email format
validate_email() {
    local email="$1"
    if [[ ! "$email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        print_error "Invalid email format: $email"
        exit 1
    fi
}

# Main script logic
main() {
    # Change to project directory
    cd "$PROJECT_DIR"
    
    print_info "Starting User Management Tool..."
    print_info "Project directory: $PROJECT_DIR"
    
    # Check virtual environment
    check_venv
    
    # Check dependencies
    check_dependencies
    
    # Parse command
    case "$1" in
        "create")
            if [[ $# -lt 3 ]]; then
                print_error "Usage: $0 create <email> <password> [--full-name <name>]"
                exit 1
            fi
            
            local email="$2"
            local password="$3"
            local full_name=""
            
            # Check for full name option
            if [[ "$4" == "--full-name" && $# -ge 5 ]]; then
                full_name="$5"
            fi
            
            validate_email "$email"
            
            print_info "Creating user: $email"
            if [[ -n "$full_name" ]]; then
                python scripts/user_manager.py create "$email" "$password" --full-name "$full_name"
            else
                python scripts/user_manager.py create "$email" "$password"
            fi
            ;;
            
        "update")
            if [[ $# -ne 3 ]]; then
                print_error "Usage: $0 update <email> <new_password>"
                exit 1
            fi
            
            local email="$2"
            local password="$3"
            
            validate_email "$email"
            
            print_info "Updating password for user: $email"
            python scripts/user_manager.py update "$email" "$password"
            ;;
            
        "list")
            print_info "Listing all users..."
            python scripts/user_manager.py list
            ;;
            
        "show")
            if [[ $# -ne 2 ]]; then
                print_error "Usage: $0 show <email>"
                exit 1
            fi
            
            local email="$2"
            validate_email "$email"
            
            print_info "Showing details for user: $email"
            python scripts/user_manager.py show "$email"
            ;;
            
        "delete")
            if [[ $# -ne 2 ]]; then
                print_error "Usage: $0 delete <email>"
                exit 1
            fi
            
            local email="$2"
            validate_email "$email"
            
            print_warning "Deleting user: $email"
            python scripts/user_manager.py delete "$email"
            ;;
            
        "help"|"-h"|"--help")
            show_usage
            ;;
            
        "")
            show_usage
            ;;
            
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
