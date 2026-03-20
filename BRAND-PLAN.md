# TechAI Explained — Brand Plan

## Mission

Deliver daily, actionable tech insights to developers and tech enthusiasts — in English and Hebrew — through automated video briefs, written content, and community engagement.

## Revenue Streams

| Stream           | Platform         | Status           | Notes                              |
|-----------------|------------------|------------------|------------------------------------|
| Digital Products | Gumroad          | ✅ Active         | Store: tdsquad.gumroad.com         |
| Ad Revenue       | Google AdSense   | ⏳ Pending signup | Needs publisher ID                 |
| Affiliates       | Multiple         | ⏳ Pending signup | DigitalOcean, AWS, Cloudflare, JetBrains |
| Tips/Donations   | BuyMeACoffee     | ⏳ Pending setup  | buymeacoffee.com/jellyboltgames    |
| Courses          | Gumroad/Udemy    | 📋 Planned        | Tech tutorial courses              |
| Newsletter       | Substack         | 📋 Planned        | Weekly Hebrew tech digest          |

## Distribution Channels

| Channel       | Purpose                      | Frequency      | Status         |
|---------------|------------------------------|----------------|----------------|
| YouTube       | Daily tech briefs (video)    | Daily          | ⏳ API pending |
| Medium        | Long-form articles           | 2-3x/week      | 📋 Planned     |
| Dev.to        | Cross-posted articles        | 2-3x/week      | 📋 Planned     |
| Hashnode      | Cross-posted articles        | 2-3x/week      | 📋 Planned     |
| Substack      | Hebrew newsletter            | Weekly          | 📋 Planned     |
| Reddit        | Community engagement         | 2-3x/week      | 📋 Planned     |
| Twitter/X     | Short updates, threads       | Daily           | 📋 Planned     |
| LinkedIn      | Professional content         | 2-3x/week      | 📋 Planned     |

## Automation

### Daily Briefs Pipeline (GitHub Actions)

- **Schedule:** 06:00 UTC daily
- **Topics:** .NET, AI, Cloud, Dev (daily) + Security, GameDev (Sundays)
- **Languages:** English + Hebrew
- **Output:** Video briefs with TTS narration
- **Storage:** GitHub artifacts (30-day retention)

### Content Calendar (GitHub Actions)

- **Schedule:** Every Monday at 07:00 UTC
- **Creates:** Weekly content plan issue + 7 daily tracking issues
- **Labels:** `content-calendar`, `daily-brief`, `automation`

### Future Automation

- YouTube auto-upload (when API keys configured)
- Medium cross-posting via API
- Social media scheduled posting
- Newsletter auto-generation from top briefs

## Hebrew Content Strategy

- Translate top-performing English briefs to Hebrew
- Hebrew-specific RSS sources in `topics_he.json`
- Noto fonts for Hebrew text rendering in videos
- Target: Hebrew tech newsletter on Substack

## Cross-Brand Promotion

| From              | To                | Method                           |
|-------------------|-------------------|----------------------------------|
| TechAI Explained  | JellyBolt Games   | GameDev briefs mention games     |
| TechAI Explained  | Content Empire    | Syndicate articles               |
| JellyBolt Games   | TechAI Explained  | Game dev tutorials               |
| Content Empire    | TechAI Explained  | Feature tech content             |

## Content Calendar

### Daily
- 4 tech brief videos (EN): .NET, AI, Cloud, Dev
- 1+ social media post

### Weekly
- Sunday: Security + GameDev briefs
- Monday: Content plan created (auto)
- Midweek: 1 long-form article
- Friday: Weekly summary video

### Monthly
- Review analytics and top-performing content
- Adjust topic weights based on engagement
- Update affiliate links and promotions

### Quarterly
- Launch or update a digital product on Gumroad
- Evaluate new revenue streams
- Review and refresh content strategy

## Key Metrics to Track

- Daily brief views (YouTube)
- Article reads (Medium, Dev.to)
- Gumroad revenue
- Affiliate conversions
- Newsletter subscribers
- Social media followers

## Session History

### March 19–20, 2026 — Major Build Session
- **Agents used:** 87 AI agents (squad pattern)
- **Files created/modified:** 250+
- **Videos generated:** 8 MP4s (4 EN + 4 HE daily briefs)

**What was built:**
- Full video pipeline: `generate_video.py` with 8 slide templates, TTS via edge-tts
- Daily brief system: news fetching → script generation → video rendering
- Hebrew content pipeline: `topics_he.json`, Hebrew TTS (he-IL-AvriNeural)
- 15 tutorial articles covering .NET, AI, K8s, cloud, DevOps
- 9 video scripts + 14 slide-formatted scripts
- 5-lesson Kubernetes course
- Eleventy static site (~36 pages)
- GitHub Actions: daily-briefs.yml (6 AM UTC cron), content-calendar.yml, deploy.yml
- Gumroad products: AI Dev Course ($19.99), K8s Course ($14.99), Game Bundle ($4.99)
- Monetization setup: AdSense placeholders, affiliate configs, FUNDING.yml
- Hebrew interview series: 48 files (C#, Algorithms, AI/ML, System Design)
- Brand detachment: removed all personal name references

**Key decisions:**
- Independent brand identity (no personal name association)
- Dual-language strategy (English + Hebrew)
- Automated daily content via GitHub Actions
- Gumroad as primary digital product platform
- Edge-tts for zero-cost TTS (no API keys needed)
- Eleventy for static site (lightweight, fast builds)
