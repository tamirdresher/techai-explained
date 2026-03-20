# fetch-credentials.ps1 — Reads config from GitHub Variables (readable)
# Passwords remain as GitHub Secrets (write-only, only available in Actions)
# Usage: .\fetch-credentials.ps1

$ErrorActionPreference = "Stop"

$repos = @{
    "techai-explained" = "techai-explained/techai-explained"
    "content-empire" = "content-empire-pub/content-empire"
    "jellybolt-games" = "jellybolt-games/jellybolt-games"
}

Write-Host "Fetching brand config from GitHub Variables..." -ForegroundColor Cyan

foreach ($brand in $repos.Keys) {
    $orgRepo = $repos[$brand]
    Write-Host "`n=== $brand ($orgRepo) ===" -ForegroundColor Yellow
    
    try {
        $vars = gh variable list --repo $orgRepo --json name,value 2>&1 | ConvertFrom-Json
        if ($vars) {
            foreach ($v in $vars) {
                Write-Host "  $($v.name) = $($v.value)"
            }
            
            # Create .env file in the local repo
            $repoPath = "C:\Users\tamirdresher\source\repos\$brand"
            if (Test-Path $repoPath) {
                $envContent = ($vars | ForEach-Object { "$($_.name)=$($_.value)" }) -join "`n"
                Set-Content "$repoPath\.env" -Value $envContent -Encoding UTF8
                Write-Host "  -> Created .env in $repoPath" -ForegroundColor Green
            }
        } else {
            Write-Host "  No variables found" -ForegroundColor Red
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nNote: Passwords are stored as GitHub Secrets (not readable via CLI)." -ForegroundColor Yellow
Write-Host "They are only available inside GitHub Actions via secrets.MAIL_TM_PASSWORD etc."
