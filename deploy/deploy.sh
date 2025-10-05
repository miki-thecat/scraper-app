#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
ARTIFACT_PATH="$BUILD_DIR/app.tar.gz"

mkdir -p "$BUILD_DIR"

tar --exclude='__pycache__' --exclude='*.pyc' --exclude='build' \
    -czf "$ARTIFACT_PATH" \
    app cli deploy docs/spec.md docs/images ml run.py requirements.txt README.md

if [[ -n "${EC2_HOST:-}" ]]; then
    TARGET_PATH="${EC2_PATH:-/var/www/scraper-app}"
    SSH_USER="${EC2_USER:-ec2-user}"
    SSH_PORT="${EC2_PORT:-22}"

    echo "Transferring artifact to ${SSH_USER}@${EC2_HOST}:${TARGET_PATH}" >&2
    scp -P "$SSH_PORT" -o StrictHostKeyChecking=no "$ARTIFACT_PATH" "${SSH_USER}@${EC2_HOST}:${TARGET_PATH}/app.tar.gz"

    REMOTE_CMD="cd ${TARGET_PATH} && tar -xzf app.tar.gz && sudo systemctl restart scraper-app"
    echo "Executing remote deploy command" >&2
    ssh -p "$SSH_PORT" -o StrictHostKeyChecking=no "${SSH_USER}@${EC2_HOST}" "$REMOTE_CMD"
else
    echo "EC2_HOST 未設定のため、リモートデプロイはスキップしました。" >&2
fi
