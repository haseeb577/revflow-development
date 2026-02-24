# Push this project to a NEW GitHub repository
# Run this AFTER creating the repo at https://github.com/new
# Your existing origin (revflow-os-config) is left unchanged.

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$remoteName = "newrepo"
git remote remove $remoteName 2>$null
git remote add $remoteName $RepoUrl

Write-Host "Pushing branches to $RepoUrl ..." -ForegroundColor Cyan
# Push master as 'main' (default branch for new repo)
git push -u $remoteName master:main
# Push revflow-dev branch
git push $remoteName revflow-dev:revflow-dev

Write-Host "`nDone! Your code is in the new repository." -ForegroundColor Green
Write-Host "Repo: $RepoUrl" -ForegroundColor Gray
