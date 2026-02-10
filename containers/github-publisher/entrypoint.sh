#!/usr/bin/env bash
# 😐 Entrypoint for anonymized GitHub publishing
# Harold's identity stays hidden

set -euo pipefail

# 😐 Dark Harold's paranoia: Validate environment
if [[ -z "${GH_TOKEN_ENCRYPTED:-}" ]]; then
    echo "😐 Error: GH_TOKEN_ENCRYPTED not provided"
    echo "Harold cannot publish without authentication"
    exit 1
fi

if [[ -z "${ENCRYPTION_KEY:-}" ]]; then
    echo "😐 Error: ENCRYPTION_KEY not provided"
    echo "Harold demands secure token handling"
    exit 1
fi

# 😐 Decrypt GitHub token in-memory only (never touch disk)
echo "😐 Decrypting GitHub authentication token..."
GH_TOKEN=$(echo "$GH_TOKEN_ENCRYPTED" | age -d -i <(echo "$ENCRYPTION_KEY") 2>/dev/null || true)

if [[ -z "$GH_TOKEN" ]]; then
    echo "😐 Error: Token decryption failed"
    echo "Harold's paranoia was justified"
    exit 1
fi

# 😐 Authenticate with gh CLI (in-memory)
echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null

# Verify authentication worked
if ! gh auth status &>/dev/null; then
    echo "😐 Error: GitHub authentication failed"
    echo "Harold remains unpublished"
    exit 1
fi

echo "😐 GitHub authentication successful (Harold smiles nervously)"

# 😐 Randomize git configuration to prevent fingerprinting
RANDOM_NAMES=(
    "Alex Chen" "Jordan Smith" "Taylor Brown" "Morgan Lee"
    "Casey Park" "Riley Johnson" "Quinn Davis" "Avery Wilson"
    "Cameron Martinez" "Dakota Anderson" "Sage Thomas"
)

RANDOM_DOMAINS=("users.noreply.github.com" "pm.me" "protonmail.com" "tutanota.com")

# 😐 Dark Harold randomizes identity
RANDOM_NAME="${RANDOM_NAMES[$((RANDOM % ${#RANDOM_NAMES[@]}))]}"
RANDOM_DOMAIN="${RANDOM_DOMAINS[$((RANDOM % ${#RANDOM_DOMAINS[@]}))]}"
RANDOM_EMAIL="${RANDOM_NAME// /}${RANDOM}@${RANDOM_DOMAIN}"
RANDOM_TIMEZONE="Etc/UTC"  # Always UTC to prevent timezone fingerprinting

# 😐 Configure git with randomized identity
git config --global user.name "$RANDOM_NAME"
git config --global user.email "$RANDOM_EMAIL"
git config --global commit.gpgsign false

echo "😐 Git identity randomized: $RANDOM_NAME <$RANDOM_EMAIL>"

# 😐 Set timezone to UTC (prevents temporal fingerprinting)
export TZ="$RANDOM_TIMEZONE"

# 😐 Clear bash history (no command leakage)
export HISTFILE=/dev/null
export HISTSIZE=0

# 😐 Disable SSH fingerprint persistence
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "StrictHostKeyChecking accept-new" > ~/.ssh/config
echo "UserKnownHostsFile /dev/null" >> ~/.ssh/config
chmod 600 ~/.ssh/config

echo "😐 Container configured for anonymized publishing"
echo "😐 Hostname obfuscated: $(hostname)"
echo "😐 User: $(whoami)"
echo "😐 Harold is ready to publish while hiding the pain"

# 😐 Execute provided command or default to bash
exec "$@"

# 😐 Cleanup happens automatically on container exit
# Harold leaves no traces
