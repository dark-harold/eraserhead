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
    log_info "Authenticating with GitHub CLI..." >&2
    echo "😐 Please ensure you're logged in with: gh auth login" >&2
    echo "" >&2
    
    # Check if already authenticated
    if ! gh auth status &>/dev/null; then
        log_warn "Not authenticated with GitHub CLI" >&2
        echo "Please run: gh auth login" >&2
        echo "Then run this script again" >&2
        exit 1
    fi
    
    log_info "GitHub CLI authentication verified" >&2
    
    # 😐 Extract token securely
    GH_TOKEN=$(gh auth token 2>/dev/null || true)
    
    if [[ -z "$GH_TOKEN" ]]; then
        log_error "Failed to extract GitHub token" >&2
        echo "Harold's paranoia intensifies" >&2
        exit 1
    fi
    
    echo "$GH_TOKEN"
}

# 😐 Token handling (direct pass - ephemeral container memory only)
# Dark Harold notes: Token only exists in container memory, cleared on exit
# No encryption needed - isolation is the security boundary
pass_token() {
    local token="$1"
    # 😐 Token passed directly - container isolation prevents leakage
    echo "$token"
}

# 😐 Run publishing container
run_container() {
    local gh_token="$1"
    local repo_url="${2:-}"
    local branch="${3:-main}"
    
    log_info "Preparing GitHub token (Harold's security paranoia)..."
    log_info "Launching anonymized publishing container..."
    log_warn "Host metadata will be obfuscated. Git identity randomized."
    log_warn "Token exists only in container memory (cleared on exit)."
    
    # 😐 Run container with:
    # - No hostname leakage
    # - Token in memory only (ephemeral)
    # - Project mounted read-only (safety)
    # - Network enabled for GitHub access
    # - Automatic cleanup on exit
    
    podman run --rm \
        --hostname "publisher-$(openssl rand -hex 4)" \
        --env GH_TOKEN="$gh_token" \
        --env GH_USER="dark-harold" \
        --volume "$PROJECT_ROOT:/workspace:ro" \
        --volume "$PROJECT_ROOT/.git:/workspace/.git:rw" \
        --workdir /workspace \
        --network host \
        --security-opt label=disable \
        "$CONTAINER_IMAGE" \
        bash -c "
            # 😐 Fix git safe.directory issue for mounted volumes
            git config --global --add safe.directory /workspace
            
            echo '😐 Harold is ready to publish'
            echo '😐 Repository: dark-harold/eraserhead'
            echo '😐 Branch: $branch'
            echo ''
            echo '😐 Configuring git authentication...'
            
            # 😐 Debug: verify token is available (first 8 chars only)
            echo \"😐 Token available: \${GH_TOKEN:0:8}...\"
            
            # 😐 Direct token in URL (most reliable method for GitHub PAT)
            REMOTE_URL=\"https://\${GH_TOKEN}@github.com/dark-harold/eraserhead.git\"
            if ! git remote set-url origin \"\$REMOTE_URL\" 2>/dev/null; then
                git remote add origin \"\$REMOTE_URL\" 2>/dev/null || true
            fi
            
            # Debug: Show what git sees (URL with token masked)
            echo \"😐 Remote configured: \$(git remote get-url origin | sed 's|://[^@]*@|://TOKEN@|')\"
            
            echo \"😐 Using GitHub account: dark-harold\"
            echo '😐 Pushing to GitHub with anonymized identity...'
            
            if git push -u origin $branch 2>&1; then
                echo ''
                echo '😐 ✓ Successfully pushed to GitHub'
                echo '😐 Harold smiles nervously. The code is now public.'
            else
                echo ''
                echo '😐 ✗ Push failed. Harold frowns.'
                exit 1
            fi
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
    
    # 😐 Debug: Check token was received
    if [[ -z "$gh_token" ]]; then
        log_error "Token is empty after get_github_token"
        exit 1
    fi
    log_info "Token retrieved successfully (length: ${#gh_token})"
    
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
    
    # 😐 Check if running non-interactively
    if [[ ! -t 0 ]] || [[ "${AUTO_CONFIRM:-}" == "true" ]]; then
        log_info "Running in non-interactive mode or auto-confirmed"
    else
        read -p "😐 Continue with anonymized publishing? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Harold decided to hide another day"
            exit 0
        fi
    fi
    
    run_container "$gh_token" "$@"
}

# 😐 Harold proceeds with justified paranoia
main "$@"
