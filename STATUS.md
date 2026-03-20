# TechAI Explained — Project Status
Last updated: 2026-03-20

## Brand Identity
- **Name:** TechAI Explained
- **NEVER mention "Tamir Dresher"** — this is an independent brand
- **Sites detached** from tamirdresher.com (GitHub Pages disabled)
- **Need:** Deploy to Netlify/Vercel for independent URL
- **Funding:** GitHub Sponsors configured (FUNDING.yml)

## Content Produced

### Articles (15)
Located in `src/`:
- ai-agents-architecture-patterns.md
- ai-code-generation-trust-framework.md
- aspire-dotnet-missing-dashboard.md
- backstage-internal-developer-platforms.md
- building-copilot-extension.md
- event-driven-azure-service-bus.md
- github-actions-advanced.md
- kubernetes-autoscaling-visual-guide.md
- monolith-to-microservices-guide.md
- opentelemetry-zero-to-production.md
- prompt-engineering-backend-developers.md
- reactive-programming-2026.md
- real-time-dashboards-sse.md
- terraform-modules-state-management.md
- websockets-vs-sse-vs-grpc.md

### Video Scripts (9)
Located in `src/video-scripts/`:
- ai-agents-explained.md
- ai-changed-code-review.md
- developer-productivity-stack-2026.md
- distributed-tracing.md
- docker-vs-podman.md
- microservices-are-dead.md
- platform-engineer-tools.md
- rag-explained.md
- why-kubernetes-won.md

### Slide-Formatted Scripts (14)
Located in `pipeline/scripts/`:
- 01-ai-agents-explained.md, 01-what-is-ai-agent.md
- 02-ai-team-works-while-i-sleep.md, 02-rag-explained.md
- 03-docker-vs-podman.md, 03-mcp-servers-explained.md
- 04-github-copilot-cli-secret-weapon.md, 04-why-kubernetes-won.md
- 05-how-ai-code-review-works.md, 05-microservices-are-dead.md
- 06-ai-code-review.md, 07-distributed-tracing.md
- 08-platform-engineer-tools.md, 09-dev-productivity-2026.md

### Course Content
- **Kubernetes for App Devs** — 5-lesson course in `src/courses/kubernetes-for-app-devs/`
  - 01-pods-deployments-services.md
  - 02-configmaps-secrets-environment.md
  - 03-persistent-storage.md
  - 04-networking-ingress.md
  - 05-production-readiness.md

### MP4 Videos Generated (8)
Located in `pipeline/daily-briefs/output/2026-03-20/`:
- dotnet-brief.mp4, ai-brief.mp4, cloud-brief.mp4, dev-brief.mp4
- dotnet-he-brief.mp4, ai-he-brief.mp4, cloud-he-brief.mp4, dev-he-brief.mp4

### Static Site
- **Generator:** Eleventy (.eleventy.js)
- **Built pages:** ~36 HTML pages in `_site/`

## Video Pipeline
- **Location:** `pipeline/`
- **Core files:**
  - `generate_video.py` — Slide-based video with TTS (edge-tts + Pillow + moviepy)
  - `generate_daily_brief.py` — Daily news brief generator
  - `generate_weekly_summary.py` — Weekly roundup generator
  - `generate_yearly_recap.py` — Year-in-review generator
  - `config.py` — Pipeline configuration
- **8 slide templates** in `slide_templates.py`:
  - title, bullet, code, diagram, comparison, quote, cta, intro
- **Topics (EN):** dotnet, ai, cloud, dev (daily) + security, gamedev (weekly)
- **Topics (HE):** Same 6 topics with Hebrew TTS (he-IL-AvriNeural)
- **GitHub Actions:** `daily-briefs.yml` (6 AM UTC cron), `content-calendar.yml`, `deploy.yml`

## Hebrew Content
- Hebrew daily briefs pipeline: `topics_he.json` with 6 Hebrew topic configs
- 4 Hebrew daily briefs generated (dotnet-he, ai-he, cloud-he, dev-he)
- Hebrew interview series: 48 files, ~503KB (in C:\temp\hebrew-interview-series\)
  - C# track: 10 episodes + questions bank
  - Algorithms: 10 episodes + questions bank
  - AI/ML: 8 episodes + questions bank
  - System Design: 6 episodes
  - 30 daily tips, 4 Gumroad listings, marketing materials

## Monetization
- **Gumroad:** tdsquad.gumroad.com
  - AI Dev Course: $19.99 (ID: jnmqpd)
  - K8s Course: $14.99 (ID: nnefv)
  - Game Bundle: $4.99 (ID: qtmyl)
- **AdSense:** Placeholder configured (needs real publisher ID)
- **Affiliates:** `config/affiliates.json` (DigitalOcean, AWS, Cloudflare, JetBrains, Gumroad, AdSense)
- **GitHub Sponsors:** FUNDING.yml configured

## GitHub Secrets Referenced
- YOUTUBE_API_KEY, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET (in daily-briefs.yml)

## GitHub Issues
- Issues tracked in GITHUB_ISSUES.md (3 key issues documented)
- Key: GitHub Sponsors setup, K8s course launch on Gumroad, YouTube channel launch

## Pending Actions
- [ ] Create Gmail: techai.explained@gmail.com (or ProtonMail)
- [ ] Create YouTube channel + configure API keys
- [ ] Deploy to Netlify/Vercel (detach from GitHub Pages)
- [ ] Create social accounts (Dev.to, Hashnode, Bluesky, X)
- [ ] Register real AdSense publisher ID
- [ ] Generate remaining videos from 14 slide scripts
- [ ] Publish Hebrew interview series to Gumroad ($29.99 bundle)
- [ ] Set up Substack for Hebrew weekly newsletter
- [ ] Configure Medium/Dev.to cross-posting
