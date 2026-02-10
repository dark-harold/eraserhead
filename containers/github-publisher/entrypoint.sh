#!/usr/bin/env bash
# 😐 Entrypoint for anonymized GitHub publishing
# Harold's identity stays hidden

set -euo pipefail

# 😐 Dark Harold's paranoia: Validate environment
if [[ -z "${GH_TOKEN:-}" ]]; then
    echo "😐 Error: GH_TOKEN not provided"
    echo "Harold cannot publish without authentication"
    exit 1
fi

echo "😐 GitHub token received (ephemeral memory only)..."

# 😐 Authenticate gh CLI for API calls (optional, non-fatal if fails)
echo "😐 Configuring GitHub CLI authentication..."
echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null || echo "😐 Note: gh CLI auth skipped (token will be used directly in git URLs)"

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
