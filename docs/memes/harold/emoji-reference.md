# Harold Persona Image Reference

*The official Hide the Pain Harold persona guide for EraserHead documentation*

**Last Updated**: February 12, 2026
**Curator**: Dark Harold (who else would catalog pain?)

---

## The Six Personas

EraserHead uses **real Harold photo images** — face crops from the iconic stock photos with persona-specific color treatments. Each persona corresponds to a documentation voice.

<p align="center">
  <img src="emoji/harold-showcase.png" alt="All six Harold personas">
</p>

<p align="center">
  <em>Standard · Dark · Historian · Shipper · Anemochory · Ultra Dark</em>
</p>

### Available Sizes

Images are available at 32px, 64px, and 128px. Place them at document headers or section breaks — not as inline text decorations.

---

## Persona Guide

### Standard Harold
**Image**: `harold-standard-128.png`
**Meaning**: The classic. Confident exterior, internal questioning of all life choices.
**Usage**: General documentation headers, welcoming sections, contributor guides.
**Voice**: *"This will definitely scale to production."*

### Dark Harold
**Image**: `harold-dark-128.png`
**Meaning**: Worst-case thinking, security paranoia, assumes everything is compromised.
**Usage**: Security documentation, threat models, cryptographic warnings.
**Voice**: *"If you think it's secure, you haven't found the vulnerability yet."*

### Internet Historian
**Image**: `harold-historian-128.png`
**Meaning**: Narrative documentation style, dry wit about disasters, engaging storytelling.
**Usage**: API references, architecture narratives, historical context.
**Voice**: *"The story of every data breach starts with 'we thought it was fine.'"*

### Effective Developer (The Shipper)
**Image**: `harold-shipper-128.png`
**Meaning**: Pragmatic delivery, ships working code, manages scope ruthlessly.
**Usage**: Implementation guides, adapter development, shipping milestones.
**Voice**: *"Shipped with 94% coverage. Good enough."*

### Anemochory Harold
**Image**: `harold-anemochory-128.png`
**Meaning**: Origin obfuscation, network anonymization, untraceable paths.
**Usage**: Anemochory protocol documentation, routing, anonymization.
**Voice**: *"Like seeds in the wind, your packets' origins are lost to time."*

### Ultra Dark Harold
**Image**: `harold-ultra-dark-128.png`
**Meaning**: When the CVE is critical, the exploit is in the wild, and the dependency chain includes it.
**Usage**: Critical security advisories, active exploitation warnings, production incidents.
**Voice**: *"CVSS 9.8. Actively exploited. Our dependency chain includes it."*

---

## Placement Guidelines

| Location | Persona | Size |
|----------|---------|------|
| README.md header | Showcase (all six) | composite |
| CONSTITUTION.md header | Dark Harold | 128px |
| CONTRIBUTING.md header | Standard Harold | 128px |
| User Guide header | Standard Harold | 128px |
| API Reference header | Historian | 128px |
| Adapter Development header | Shipper | 128px |
| Security docs | Dark / Ultra Dark | 128px |

### Principles

- **Sparse**: One image per document header. Maybe one mid-doc at a key section break.
- **Contextual**: Match the persona to the document's tone.
- **Centered**: Use `<p align="center">` blocks for clean presentation.
- **Not inline**: These are section-level images, not text-level decorations.

---

## Regeneration

```bash
python scripts/fetch-harold-emoji.py
```

Pipeline: downloads source photo → crops face → applies color treatment → generates sizes.

---

## Harold's Approval

*"I've made a career out of hiding pain. Now I'm hiding it in strategically placed documentation images."* — Harold (probably)

For sourcing, copyright, and Harold lore, see [MEME-GALLERY.md](MEME-GALLERY.md).
