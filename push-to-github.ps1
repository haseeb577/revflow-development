# Push this project to your new GitHub repo
# Run this AFTER creating the repo on https://github.com/new

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Remove default origin if it exists (e.g. from fork)
git remote remove origin 2>$null

git remote add origin $RepoUrl
git branch -M main
Write-Host "Pushing to $RepoUrl ..." -ForegroundColor Cyan
git push -u origin main

Write-Host "`nDone! Your code is on GitHub." -ForegroundColor Green
