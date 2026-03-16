# Ralph Watch — TechAI Explained
# Monitors video pipeline and content schedule

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "ERROR: Ralph Watch requires PowerShell 7+" -ForegroundColor Red
    exit 1
}

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Ralph Watch - techai-explained"

$repoOwner = "tamirdresher"
$repoName = "techai-explained"
$round = 0
$consecutiveFailures = 0
$roundTimeoutMinutes = 30
$sleepSeconds = 300

$prompt = @'
Ralph, Go! Check the open issues in this repo and work on any that are actionable.
Follow the routing rules in .squad/routing.md to assign work to the right agents.
Focus on the video production pipeline — scripts, voice, visuals, SEO, and publishing.
If there are no actionable issues, report idle status.
'@

function ghp { gh auth switch --user tamirdresher 2>$null | Out-Null; gh @args }

while ($true) {
    $round++
    $roundStart = Get-Date
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "`n$timestamp — Ralph Round $round Start" -ForegroundColor Cyan

    # Step 1: List open issues for visibility
    $issues = ghp issue list --repo "$repoOwner/$repoName" --state open --json number,title,labels 2>$null | ConvertFrom-Json
    if ($issues) {
        Write-Host "  Open issues: $($issues.Count)" -ForegroundColor Yellow
        foreach ($issue in $issues) {
            Write-Host "    #$($issue.number): $($issue.title)" -ForegroundColor Gray
        }
    }

    # Step 2: Run agency copilot
    $exitCode = 0
    $roundStatus = "idle"

    if ($issues -and $issues.Count -gt 0) {
        try {
            $ErrorActionPreference_saved = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"

            # Fresh session per round to prevent history accumulation
            $roundSessionId = [guid]::NewGuid().ToString()

            # Write prompt to temp file to avoid Start-Process argument splitting
            # (embedded flags like -R in prompt text get misinterpreted as CLI args)
            $promptFile = Join-Path $env:TEMP "ralph-prompt-techai-$round.txt"
            [System.IO.File]::WriteAllText($promptFile, $prompt, [System.Text.Encoding]::UTF8)

            # Create a thin wrapper script that reads the prompt from file and calls agency
            # This avoids ALL Start-Process argument quoting issues
            $wrapperScript = Join-Path $env:TEMP "ralph-round-techai-$round.ps1"
            @"
`$promptFile = '$($promptFile.Replace("'","''"))'
`$p = [System.IO.File]::ReadAllText(`$promptFile)
`$singleLine = `$p -replace "`r`n", " " -replace "`n", " "
agency copilot --yolo --autopilot --agent squad -p `$singleLine --resume=$roundSessionId
exit `$LASTEXITCODE
"@ | Out-File -FilePath $wrapperScript -Encoding utf8 -Force

            # Launch the wrapper script with timeout guard
            $agencyProc = Start-Process -FilePath "pwsh" `
                -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $wrapperScript) `
                -PassThru -NoNewWindow
            $timedOut = $false
            $timeoutMs = $roundTimeoutMinutes * 60 * 1000
            if (-not $agencyProc.WaitForExit($timeoutMs)) {
                $timedOut = $true
                Write-Host "[$((Get-Date -Format 'HH:mm:ss'))] TIMEOUT: Round $round exceeded ${roundTimeoutMinutes}m limit — killing agency process (PID $($agencyProc.Id))" -ForegroundColor Red
                try {
                    $childProcs = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $agencyProc.Id }
                    foreach ($child in $childProcs) {
                        Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
                    }
                    Stop-Process -Id $agencyProc.Id -Force -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "  Warning: Could not kill all child processes: $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
            $exitCode = if ($timedOut) { 124 } else { $agencyProc.ExitCode }
            $ErrorActionPreference = $ErrorActionPreference_saved

            if ($timedOut) {
                $consecutiveFailures++
                $roundStatus = "timeout"
            } elseif ($exitCode -eq 0) {
                $consecutiveFailures = 0
                $roundStatus = "idle"
            } else {
                $consecutiveFailures++
                $roundStatus = "error"
            }
        } catch {
            Write-Host "[$timestamp] Error: $($_.Exception.Message)" -ForegroundColor Red
            $exitCode = 1
            $consecutiveFailures++
            $roundStatus = "error"
        }
    } else {
        Write-Host "  No open issues — skipping agency round" -ForegroundColor DarkGray
    }

    $elapsed = (Get-Date) - $roundStart
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') — Round $round complete ($([int]$elapsed.TotalSeconds)s) [status=$roundStatus, failures=$consecutiveFailures]" -ForegroundColor Green

    # Back off if failing repeatedly
    $backoffSeconds = if ($consecutiveFailures -ge 3) { $sleepSeconds * 2 } else { $sleepSeconds }
    Start-Sleep -Seconds $backoffSeconds
}
