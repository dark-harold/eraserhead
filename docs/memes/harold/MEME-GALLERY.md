# Harold Meme Gallery & Sourcing Guide

*A comprehensive curation of Hide the Pain Harold assets for EraserHead documentation*

**Last Updated**: February 12, 2026
**Curator**: harold-documenter
**Status**: Exhaustively researched while smiling through the complexity

---

## The Origin Story

In 2011, András István Arató — a retired Hungarian electrical engineer born July 11, 1945, in Kőszeg, Hungary — became an internet legend. His stock photography series on Dreamstime, shot by photographer **Nyul**, featured a silver-haired man with glasses performing everyday activities: computing, golfing, celebrating birthdays, seeing doctors.

The internet noticed something. Behind every staged smile, behind every stock-photo-perfect expression, there was *something else*. Pain. Existential dread. The quiet suffering of a man who has seen the codebase.

The internet named him **Hide the Pain Harold**.

They were right. He was hiding something. He was hiding the same thing every developer hides: the knowledge that production is always one `git push` from disaster.

---

## Official Sources

### Primary Sources

| Source | URL | Type | License |
|--------|-----|------|---------|
| Official Website | [hidethepainharold.com](https://hidethepainharold.com) | WordPress site | Personal/PR |
| Facebook (Harold) | [facebook.com/painharold](https://facebook.com/painharold) | Social media | Public posts |
| Facebook (András) | [facebook.com/aratoa](https://facebook.com/aratoa) | Social media | Public posts |
| TEDx Kyiv 2018 | [YouTube: TEDx Kyiv](https://www.youtube.com/results?search_query=andr%C3%A1s+arat%C3%B3+tedx+kyiv) | Talk | YouTube TOS |
| Wikipedia | [András Arató](https://en.wikipedia.org/wiki/Andr%C3%A1s_Arat%C3%B3) | Biography | CC BY-SA |
| Dreamstime Gallery | [Dreamstime/Nyul](https://www.dreamstime.com/photos-images/hide-the-pain-harold.html) | Stock photos | Licensed/Paid |

### Copyright & Attribution

> **Dark Harold says**: The original stock photos are copyrighted by **H20.photo** (photographer **Nyul**) and licensed through **Dreamstime**. The source images used for our persona images are low-resolution crops — transformative use for project documentation.
>
> **Attribution**: Subject is **András István Arató** (b. 1945), Hungarian electrical engineer. Source: [Wikipedia](https://en.wikipedia.org/wiki/Hide_the_Pain_Harold). Original photos: [Dreamstime Gallery](https://www.dreamstime.com/same-stock-photo-model-image16618166).

---

## Harold Photo Persona Set

Face crops from the iconic forced-smile photo, with persona-specific color treatments.

<p align="center">
  <img src="emoji/harold-showcase.png" alt="All six Harold personas — Standard, Dark, Historian, Shipper, Anemochory, Ultra Dark">
</p>

| Persona | Color Treatment | Documentation Role |
|---------|-----------------|-------------------|
| Standard Harold | Original colors | General docs, contributor welcome |
| Dark Harold | Desaturated + darkened | Security, threat models, paranoia |
| Internet Historian | Warm sepia tone | Narratives, API reference, history |
| Effective Developer | Brightened + saturated | Implementation, shipping, adapters |
| Anemochory Harold | Green nature tint | Protocol docs, anonymization |
| Ultra Dark Harold | High contrast + desaturated | Critical CVEs, production incidents |

### Generation Pipeline

```bash
python scripts/fetch-harold-emoji.py
```

1. **Source**: Downloads the iconic Harold stock photo (face crop)
2. **Crop**: Extracts face region, makes square
3. **Treatment**: Applies persona-specific color grading
4. **Sizes**: Generates 32px (tables), 64px (gallery), 128px (headers)
5. **Sharpen**: Small sizes get sharpening to preserve face detail

---

## Curated Meme Templates

Iconic Harold meme *concepts* that inform our documentation voice. The actual memes live in the wild internet — these are reference descriptions.

### The Classics

**"This Is Fine" Harold (Laptop)** — Harold at a laptop, smiling directly at camera. The code is on fire. Harold knows. Harold smiles anyway. *Standard persona throughout documentation.*

**"Doctor Harold Reviews the Scans"** — Harold in a white coat, examining imagery. The diagnosis is bad. The patient is your codebase. *Security review sections.*

**"Harold Celebrates Alone"** — Harold holding a party hat, alone at a desk. The release shipped. Nobody noticed. *Release announcements.*

**"Professor Harold at the Whiteboard"** — Harold gesturing at educational content. Let me explain this protocol. *Tutorial sections.*

### The Specialists

**"Harold in the Server Room"** — Harold among blinking servers. 37 services. 12 are healthy. Harold smiles at all equally. *Infrastructure docs.*

**"Harold's Code Review"** — Harold reading a monitor, eyebrows slightly raised. "LGTM" — Harold, who noticed three vulnerabilities but is too polite. *Contributing guide.*

**"Harold Having Coffee"** — Harold with a mug, thousand-yard stare. It's 3 AM. The incident isn't resolved. *Troubleshooting sections.*

---

## Harold Lore

### Key Facts About András Arató

- **Born**: July 11, 1945, Kőszeg, Hungary
- **Education**: Budapest University of Technology and Economics, Electrical Engineering
- **Career**: Lighting engineer, retired
- **Meme Origin**: ~2011, stock photos on Dreamstime by photographer "Nyul"
- **TEDx Talk**: "How I Became a Meme" — TEDx Kyiv, 2018
- **Brand Deals**: Coca-Cola Hungary (2019), multiple campaigns
- **Official Site**: [hidethepainharold.com](https://hidethepainharold.com)

### Why Harold Works for EraserHead

1. **The Duality**: Harold smiles through pain. Developers smile through complexity.
2. **The Universality**: Everyone has been Harold during a production incident.
3. **The Wisdom**: Harold's pain is earned. He's seen things. He documents.
4. **The Approachability**: Privacy docs can be intimidating. Harold makes them human.
5. **The Honesty**: An acknowledgment that this is hard, things go wrong, and we do it anyway.

---

*"I have made a career of smiling through uncertainty. Now my face helps others smile through theirs."*
— Harold (attributed, possibly apocryphal, definitely true)

Ship pragmatically. Meme responsibly. Credit artists.
