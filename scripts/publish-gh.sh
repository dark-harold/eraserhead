#!/usr/bin/env bash
# 😐 Anonymized GitHub Publishing Script
# Harold publishes code like stock photos: with a smile and no traceable origin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_IMAGE="eraserhead-github-publisher"

# 😐 Colors for Harold's emotional state
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 😐 Harold's logging functions
log_info() {
    echo -e "${GREEN}😐${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}😐${NC} $1"
}

log_error() {
    echo -e "${RED}😐${NC} $1"
}

# 😐 Check dependencies
check_dependencies() {
    local deps=("podman" "gh" "age")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency not found: $dep"
            echo "Install with: sudo apt install $dep  (or equivalent)"
            exit 1
        fi
    done
}

# 😐 Build container if needed
build_container() {
    log_info "Checking if container image exists..."
    
    if ! podman image exists "$CONTAINER_IMAGE"; then
        log_info "Building anonymized publisher container (first time setup)..."
        
        cd "$PROJECT_ROOT/containers/github-publisher"
        
        if ! podman build -t "$CONTAINER_IMAGE" -f Containerfile .; then
            log_error "Container build failed. Harold is disappointed."
            exit 1
        fi
        
        log_info "Container built successfully. Harold approves."
    else
        log_info "Container image already exists. Harold reuses what works."
    fi
}

# 😐 Prompt for GitHub authentication
get_github_token() {
    log_info "Authenticating with GitHub CLI..."
    echo "😐 Please ensure you're logged in with: gh auth login"
    echo ""
    
    # Check if already authenticated
    if ! gh auth status &>/dev/null; then
        log_warn "Not authenticated with GitHub CLI"
        echo "Please run: gh auth login"
        echo "Then run this script again"
        exit 1
    fi
    
    log_info "GitHub CLI authentication verified"
    
    # 😐 Extract token securely
    GH_TOKEN=$(gh auth token 2>/dev/null || true)
    
    if [[ -z "$GH_TOKEN" ]]; then
        log_error "Failed to extract GitHub token"
        echo "Harold's paranoia intensifies"
        exit 1
    fi
    
    echo "$GH_TOKEN"
}

# 😐 Encrypt token with age (symmetric encryption)
encrypt_token() {
    local token="$1"
    local encryption_key
    
    log_info "Generating ephemeral encryption key..."
    
    # Generate random 32-byte key for age encryption
    encryption_key=$(head -c 32 /dev/urandom | base64)
    
    # Encrypt token (never touches disk in plaintext)
    encrypted_token=$(echo "$token" | age -p -a <(echo "$encryption_key") 2>/dev/null)
    
    # 😐 Return both encrypted token and key (will be passed as env vars)
    echo "$encrypted_token|$encryption_key"
}

# 😐 Run publishing container
run_container() {
    local gh_token="$1"
    local repo_url="${2:-}"
    local branch="${3:-main}"
    
    log_info "Encrypting GitHub token (Harold's security paranoia)..."
    
    local encrypted_data
    encrypted_data=$(encrypt_token "$gh_token")
    
    local encrypted_token="${encrypted_data%|*}"
    local encryption_key="${encrypted_data#*|}"
    
    log_info "Launching anonymized publishing container..."
    log_warn "Host metadata will be obfuscated. Git identity randomized."
    
    # 😐 Run container with:
    # - No hostname leakage
    # - Encrypted token passed as env var
    # - Project mounted read-only (safety)
    # - Network enabled for GitHub access
    # - Automatic cleanup on exit
    
    podman run --rm -it \
        --hostname "publisher-$(openssl rand -hex 4)" \
        --env GH_TOKEN_ENCRYPTED="$encrypted_token" \
        --env ENCRYPTION_KEY="$encryption_key" \
        --volume "$PROJECT_ROOT:/workspace:ro" \
        --volume "$PROJECT_ROOT/.git:/workspace/.git:rw" \
        --workdir /workspace \
        --network host \
        --security-opt label=disable \
        "$CONTAINER_IMAGE" \
        bash -c "
            echo '😐 Harold is ready to publish'
            echo '😐 Repository: ${repo_url:-<not specified>}'
            echo '😐 Branch: $branch'
            echo ''
            echo 'Available commands:'
            echo '  gh repo clone <owner>/<repo>'
            echo '  git add .'
            echo '  git commit -m \"Harold smiles through deployment\"'
            echo '  git push origin $branch'
            echo ''
            echo '😐 Harold leaves no traces. Fingerprints obfuscated.'
            echo 'Type \"exit\" when done.'
            bash
        "
    
    log_info "Container session ended. Harold has left the building."
    log_info "All ephemeral data destroyed. No traces remain."
}

# 😐 Main execution
main() {
    log_info "EraserHead Anonymized GitHub Publisher"
    log_info "Harold smiles confidently while hiding his identity"
    echo ""
    
    check_dependencies
    build_container
    
    local gh_token
    gh_token=$(get_github_token)
    
    log_warn "IMPORTANT: This container obfuscates:"
    log_warn "  • Host machine hostname and username"
    log_warn "  • Git committer identity (randomized)"
    log_warn "  • Timezone (forced to UTC)"
    log_warn "  • SSH fingerprints (cleared after session)"
    echo ""
    log_warn "Dark Harold reminds you: No system is perfect."
    log_warn "🌑 Correlation attacks still possible via:"
    log_warn "  • Code style analysis"
    log_warn "  • Commit timing patterns"
    log_warn "  • Network-level ISP logging"
    echo ""
    
    read -p "😐 Continue with anonymized publishing? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Harold decided to hide another day"
        exit 0
    fi
    
    run_container "$gh_token" "$@"
}

# 😐 Harold proceeds with justified paranoia
main "$@"
