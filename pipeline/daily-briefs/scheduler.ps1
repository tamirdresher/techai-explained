# Daily Brief Scheduler for TechAI Explained
# Run this as a Windows Scheduled Task or keep running in background

param(
    [int]$IntervalHours = 24,
    [string]$RunTime = "06:00"  # Generate briefs at 6 AM
)

$repoRoot = "C:\Users\tamirdresher\source\repos\techai-explained"
$pipelineDir = "$repoRoot\pipeline\daily-briefs"

# Topics to generate daily
$dailyTopics = @("dotnet", "ai", "cloud", "dev")
# Topics to generate weekly (on Sundays)
$weeklyTopics = @("security", "gamedev")

function New-FailureIssue {
    param(
        [string]$Date,
        [string]$Topic,
        [string]$Language,
        [string]$Problem
    )

    $searchTitle = "TechAI Failure $Topic $Date"
    $existing = gh issue list --repo tamirdresher/techai-explained --search $searchTitle 2>$null

    if ($existing) {
        Write-Host "  [Skip] GitHub issue already exists for $Topic ($Language) on $Date" -ForegroundColor DarkGray
        return
    }

    $title = "[TechAI Failure] $Topic $Language brief failed on $Date"
    $body = "## Daily Brief Generation Failed`n`n- **Topic:** $Topic`n- **Language:** $Language`n- **Date:** $Date`n- **Problem:** $Problem`n`nCheck logs in: pipeline/daily-briefs/output/$Date/`n`n**Auto-created by scheduler.**"

    Write-Host "  [Issue] Creating GitHub issue: $title" -ForegroundColor Red
    gh issue create --repo tamirdresher/techai-explained `
        --title $title `
        --body $body `
        --label "bug"
}

function Assert-BriefOutputs {
    param(
        [string]$Date,
        [string]$Topic,
        [string]$PipelineDir
    )

    $minSizeBytes = 50 * 1024  # 50 KB

    $enFile = "$PipelineDir\output\$Date\$Topic-brief.mp4"
    if (-not (Test-Path $enFile)) {
        New-FailureIssue -Date $Date -Topic $Topic -Language "English" -Problem "Output file missing: $enFile"
    } elseif ((Get-Item $enFile).Length -lt $minSizeBytes) {
        New-FailureIssue -Date $Date -Topic $Topic -Language "English" -Problem "Output file too small ($([Math]::Round((Get-Item $enFile).Length/1KB, 1)) KB < 50 KB): $enFile"
    }

    $heFile = "$PipelineDir\output\$Date\$Topic-he-brief.mp4"
    if (-not (Test-Path $heFile)) {
        New-FailureIssue -Date $Date -Topic $Topic -Language "Hebrew" -Problem "Output file missing: $heFile"
    } elseif ((Get-Item $heFile).Length -lt $minSizeBytes) {
        New-FailureIssue -Date $Date -Topic $Topic -Language "Hebrew" -Problem "Output file too small ($([Math]::Round((Get-Item $heFile).Length/1KB, 1)) KB < 50 KB): $heFile"
    }
}

function Generate-DailyBriefs {
    param([string]$Date)

    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Generating daily briefs for $Date" -ForegroundColor Cyan

    foreach ($topic in $dailyTopics) {
        Write-Host "  Fetching news for: $topic" -ForegroundColor Yellow
        python "$pipelineDir\fetch_news.py" $topic $Date

        $briefJson = "$pipelineDir\output\$Date\$topic-brief.json"
        if (Test-Path $briefJson) {
            Write-Host "  Generating English video for: $topic" -ForegroundColor Green
            python "$pipelineDir\generate_brief_video.py" $briefJson --language en

            Write-Host "  Generating Hebrew video for: $topic" -ForegroundColor Blue
            python "$pipelineDir\generate_hebrew_brief.py" $briefJson --language he
        }

        Assert-BriefOutputs -Date $Date -Topic $topic -PipelineDir $pipelineDir
    }

    # Check if Sunday for weekly topics
    if ((Get-Date $Date).DayOfWeek -eq 'Sunday') {
        foreach ($topic in $weeklyTopics) {
            Write-Host "  Generating weekly brief for: $topic" -ForegroundColor Magenta
            python "$pipelineDir\fetch_news.py" $topic $Date
            $briefJson = "$pipelineDir\output\$Date\$topic-brief.json"
            if (Test-Path $briefJson) {
                python "$pipelineDir\generate_brief_video.py" $briefJson --language en
                python "$pipelineDir\generate_hebrew_brief.py" $briefJson --language he
            }

            Assert-BriefOutputs -Date $Date -Topic $topic -PipelineDir $pipelineDir
        }
    }

    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - All briefs generated (English + Hebrew)!" -ForegroundColor Green

    # Upload to YouTube if credentials are available
    if ($env:YOUTUBE_REFRESH_TOKEN) {
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Uploading briefs to YouTube..." -ForegroundColor Cyan
        python "$pipelineDir\upload_to_youtube.py" --date $Date --language both
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - YouTube upload complete." -ForegroundColor Green
    } else {
        Write-Host "  [Skip] YOUTUBE_REFRESH_TOKEN not set — skipping YouTube upload." -ForegroundColor DarkGray
    }
}

function Start-Scheduler {
    Write-Host "TechAI Daily Brief Scheduler Started" -ForegroundColor Cyan
    Write-Host "Generating briefs every $IntervalHours hours at $RunTime" -ForegroundColor Yellow
    Write-Host "Daily topics: $($dailyTopics -join ', ')"
    Write-Host "Weekly topics: $($weeklyTopics -join ', ') (Sundays only)"
    Write-Host "Languages: English + Hebrew (RTL)"
    Write-Host ""

    while ($true) {
        $now = Get-Date
        $targetTime = Get-Date -Hour ([int]$RunTime.Split(':')[0]) -Minute ([int]$RunTime.Split(':')[1]) -Second 0

        if ($now -gt $targetTime) {
            $targetTime = $targetTime.AddDays(1)
        }

        $waitSeconds = ($targetTime - $now).TotalSeconds
        Write-Host "Next run at: $targetTime (waiting $([Math]::Round($waitSeconds/3600, 1)) hours)"

        Start-Sleep -Seconds $waitSeconds

        $today = Get-Date -Format 'yyyy-MM-dd'
        Generate-DailyBriefs -Date $today
    }
}

# If called with -Now, generate immediately
if ($args -contains '-Now') {
    Generate-DailyBriefs -Date (Get-Date -Format 'yyyy-MM-dd')
} else {
    Start-Scheduler
}
