#!/usr/bin/env bash

CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
PACKAGE_CONFIG="$CURRENT_DIR/nuitka-package.config.yml"

set -euo pipefail
RELEASE_NAME="motion-mask-linux"

# Project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Директория для выходных артефактов
OUTPUT_DIR="$ROOT_DIR/dist/linux"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

echo "==> Building with Nuitka (standalone mode)..."
uv run python -m nuitka \
    --mode=standalone \
    --no-deployment-flag=self-execution \
    --user-package-configuration-file="$PACKAGE_CONFIG" \
    --assume-yes-for-downloads \
    --enable-plugin=no-qt \
    --output-dir="$OUTPUT_DIR" \
    --output-filename=motion-mask \
    --remove-output \
    src/motion_mask/main.py

echo "==> Nuitka build complete."

DIST_DIR="$OUTPUT_DIR/main.dist"

echo "==> Copying resources..."
cp -r "$ROOT_DIR/src/motion_mask/avatars" "$DIST_DIR/"
cp -r "$ROOT_DIR/src/motion_mask/landmarkers" "$DIST_DIR/"
cp -r "$ROOT_DIR/src/motion_mask/settings" "$DIST_DIR/"

echo "==> Copying launchers..."
cp -r "$ROOT_DIR/launchers/linux/." "$DIST_DIR/"

# Делаем скрипты исполняемыми
chmod +x "$DIST_DIR"/*.sh 2>/dev/null || true

# Создаём финальный архив
echo "==> Creating archive..."
cd "$OUTPUT_DIR"
tar -czf "$RELEASE_NAME.tar.gz" -C main.dist .

echo "==> Done: $OUTPUT_DIR/motion-mask-linux.tar.gz"