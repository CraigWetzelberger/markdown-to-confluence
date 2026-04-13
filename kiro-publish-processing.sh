#!/bin/bash
# Usage: kiro-publish-processing.sh <source.md> <output_dir>
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTPUT_DIR="${2:-$SCRIPT_DIR/output}"

rm -rf "$OUTPUT_DIR"
python3 "$SCRIPT_DIR/md2conf-mermaid.py" "$INPUT_FILE" "$OUTPUT_DIR"
