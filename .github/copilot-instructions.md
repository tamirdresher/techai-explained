## Content Empire — Agent Instructions (TechAI Explained)

### First-Time Machine Setup
1. Check pipeline/machines/registry.json — is this machine registered?
2. If NOT: run `powershell -File pipeline/bootstrap.ps1 -Install`
3. If YES: bootstrap runs automatically at logon

### Key Files to Read
- STATUS.md — Full project status, what's built, what's pending
- BRAND-PLAN.md — Revenue strategy, distribution channels, content calendar
- SESSION-LOG-2026-03-19-20.md — Comprehensive session history

### Core Rules
- NEVER mention "Tamir Dresher" — this brand is independent
- All content in English AND Hebrew
- Read STATUS.md before doing any work
- Check GitHub issues for tracked tasks

### Project Overview
This is the TechAI Content Empire — an automated pipeline for generating daily tech brief videos.
- **pipeline/machine-manifest.json** — central config for repos, tasks, and machine setup
- **pipeline/machines/registry.json** — tracks which machines are registered and their setup status
- **pipeline/bootstrap.ps1** — runs on every boot; auto-detects new machines and runs full setup
- **STATUS.md** — current project state, priorities, and context
- **SESSION-LOG-2026-03-19-20.md** — Full session log from the March 19-20 launch session


## GitHub Organization

This repo is forked into **github.com/techai-explained/techai-explained** — the brand's independent org.

**Remotes:**
- `origin` → tamirdresher/techai-explained (personal, legacy)
- `org` → techai-explained/techai-explained (org, primary going forward)

**Push to BOTH remotes** when making changes:
`git push origin main && git push org main`

**GitHub Actions Secrets (available on org repo):**
- `BRAND_EMAIL` — Brand contact email
- `BRAND_NAME` — Display name
- `GUMROAD_STORE_URL` — Gumroad storefront
- `GUMROAD_AI_COURSE_ID` — AI course product ID
- `GUMROAD_K8S_COURSE_ID` — K8s course product ID
- `EDGE_TTS_VOICE_EN` — English TTS voice
- `EDGE_TTS_VOICE_HE` — Hebrew TTS voice
- `ADSENSE_PUBLISHER_ID` — AdSense publisher
- `GUMROAD_ACCESS_TOKEN` — Gumroad API token

**Pages URL:** techai-explained.github.io/techai-explained

**⚠️ NEVER reference 'tamirdresher' or 'Tamir Dresher' in any public-facing content.**

## Credential Access (Cross-Machine)

Config is stored as **GitHub Variables** (readable) and passwords as **GitHub Secrets** (write-only).

**Reading variables (any machine with gh auth):**
```
gh variable list --repo {org}/{repo}
gh variable get BRAND_EMAIL --repo {org}/{repo}
```

**In GitHub Actions workflows:**
- Variables: `${{ vars.BRAND_NAME }}`
- Secrets: `${{ secrets.MAIL_TM_PASSWORD }}`

**Quick fetch all config for this brand:**
```
gh variable list --repo {org}/{repo} --json name,value
```

**Never commit credentials to the repo.** Use variables/secrets for all config.

