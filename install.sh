#!/usr/bin/env bash
set -e
here="$(cd "$(dirname "$0")" && pwd)"; dest=~/.claude
mkdir -p "$dest/skills"
cp -r "$here/skills/." "$dest/skills/"
if [ ! -f "$dest/CLAUDE.md" ]; then cp "$here/CLAUDE.md" "$dest/CLAUDE.md"
else echo "CLAUDE.md exists, left untouched. Merge manually from $here/CLAUDE.md"; fi
echo "Done. Restart Claude Code."
