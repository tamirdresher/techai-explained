# Decisions Log

## 2026-04-01 — Visual-First Content Standard (MANDATORY)

**Decision:** All content produced by this team MUST be visually rich. Text-heavy slides, bullet-only videos, and plain-text presentations are no longer acceptable.

**Rationale:** Current videos are too text-oriented. Humans process visuals 60,000x faster than text. Competing tech channels use rich diagrams, animations, and graphics. Our content must match or exceed that standard to grow the audience and retain viewers.

**What changes:**
1. **Scripts** (Marlowe): Every section must include `[VISUAL: ...]` annotations describing the on-screen graphics
2. **Visuals** (Velma): Every slide must include diagrams, icons, illustrations, or animations — never text-only
3. **Pipeline**: New slide types added: `[INFOGRAPHIC]`, `[ANIMATION]`, `[ICON_GRID]`
4. **Review gate**: Velma blocks any content that fails the visual richness check
5. **Daily briefs**: Even automated briefs must include topic-relevant icons and visual layouts

**Applies to:** All content types — video scripts, daily briefs, weekly summaries, thumbnails, blog hero images.

**Owner:** Velma (enforcement), Sam (approval), Marlowe (script compliance)
