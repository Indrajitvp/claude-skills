# Copies skills (and CLAUDE.md if none exists) into ~/.claude
$dest = Join-Path $env:USERPROFILE ".claude"
New-Item -ItemType Directory -Force "$dest\skills" | Out-Null
Copy-Item "$PSScriptRoot\skills\*" "$dest\skills" -Recurse -Force
if (-not (Test-Path "$dest\CLAUDE.md")) { Copy-Item "$PSScriptRoot\CLAUDE.md" "$dest\CLAUDE.md" }
else { Write-Host "CLAUDE.md exists, left untouched. Merge manually from $PSScriptRoot\CLAUDE.md" }
Write-Host "Done. Restart Claude Code."
