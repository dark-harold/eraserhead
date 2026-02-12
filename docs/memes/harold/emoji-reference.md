# 😐 Harold Emoji Reference

*The official Hide the Pain Harold emoji lexicon for EraserHead documentation*

**Last Updated**: February 12, 2026  
**Curator**: Dark Harold (who else would catalog pain?)

---

## Custom SVG Emoji Assets

EraserHead includes a set of **original custom SVG emoji** inspired by Harold's expressions. These are 128x128 vector art files — 100% original creations, no copyrighted material embedded.

| File | Persona | Emoji | Mood |
|------|---------|-------|------|
| [`emoji/harold-standard.svg`](emoji/harold-standard.svg) | 😐 Standard Harold | Forced smile | "Everything is fine" |
| [`emoji/harold-dark.svg`](emoji/harold-dark.svg) | 🌑 Dark Harold | Narrowed suspicion | "Assume compromise" |
| [`emoji/harold-historian.svg`](emoji/harold-historian.svg) | 📺 Internet Historian | Wry narrator smirk | "Let me tell you a story" |
| [`emoji/harold-shipper.svg`](emoji/harold-shipper.svg) | ✅ Effective Developer | Thumbs up, green glow | "Tests pass, ship it" |
| [`emoji/harold-anemochory.svg`](emoji/harold-anemochory.svg) | 🌱 Anemochory Harold | Peaceful, wind-blown | "One with the protocol" |
| [`emoji/harold-ultra-dark.svg`](emoji/harold-ultra-dark.svg) | ⚠️ Ultra Dark Harold | Bloodshot, cracked glasses | "The CVE is critical" |

> 📺 For the full meme sourcing guide, galleries, and Harold lore, see [MEME-GALLERY.md](MEME-GALLERY.md)

---

## Core Harold Personas

### 😐 Hide the Pain Harold (Standard)
**Meaning**: The classic. Confident exterior, internal questioning of all life choices.  
**Usage**: General commentary, acknowledging complexity, shipping despite concerns  
**Example**: *"😐 This will definitely scale to production"*

**When to use**:
- Acknowledging technical debt while moving forward
- Documenting known limitations with a smile
- General Harold commentary on any situation

---

### 🌑 Dark Harold (The Paranoid)
**Meaning**: Worst-case thinking, security paranoia, assumes everything is compromised.  
**Usage**: Security warnings, threat modeling, edge cases, cryptographic concerns  
**Example**: *"🌑 If you think it's secure, you haven't found the vulnerability yet"*

**When to use**:
- Security warnings and threat analysis
- Cryptographic design decisions
- Documenting what will inevitably fail
- Paranoid assumptions about adversaries

---

### 📺 Internet Historian (The Narrator)
**Meaning**: Narrative documentation style, dry wit about disasters, engaging storytelling.  
**Usage**: Historical context, library evaluations, architecture stories, post-mortems  
**Example**: *"📺 The story of every data breach starts with 'we thought it was fine'"*

**When to use**:
- Architecture Decision Records (ADRs)
- Library research documentation
- Post-mortem incident reports
- Historical context for technical decisions

---

### ✅ Effective Developer (The Shipper)
**Meaning**: Pragmatic delivery, ships working code, manages scope ruthlessly.  
**Usage**: Implementation notes, test completion, shipping milestones  
**Example**: *"✅ Shipped with 94% coverage. Good enough."*

**When to use**:
- Marking completed tasks
- Pragmatic scope decisions
- Test coverage milestones
- Working code delivery

---

## Thematic Emoji

### 🌱 Anemochory (Seeds in the Wind)
**Meaning**: Origin obfuscation, network anonymization, untraceable paths.  
**Usage**: References to the Anemochory protocol, packet routing, anonymization  
**Example**: *"🌱 Like seeds in the wind, your packets' origins are lost to time"*

**When to use**:
- Anemochory protocol documentation
- Network routing and anonymization discussions
- Origin obfuscation concepts

---

## Extended Persona: Ultra Dark Harold ⚠️

### ⚠️ Ultra Dark Harold (The Breach Witness)
**Meaning**: When the CVE is critical, the exploit is in the wild, and the dependency chain includes it.
**Usage**: Critical security advisories, active exploitation warnings, production incidents
**Example**: *"⚠️ CVSS 9.8. Actively exploited. Our dependency chain includes it."*

**When to use**:
- Critical security vulnerabilities (CVSS ≥ 9.0)
- Active exploitation in the wild
- Production incident documentation
- Dependency chain compromise

**Visual**: Bloodshot eyes, cracked glasses, grimace line. Harold has been awake for 72 hours.

---

## Context-Specific Guidelines

### Security Documentation
Primary emoji: 🌑 (Dark Harold paranoia mandatory)  
Secondary: 😐 (acknowledging the pain of security work)  
Avoid: ✅ (nothing is ever fully secure)

### Architecture Design
Primary emoji: 📺 (narrative depth required)  
Secondary: 😐 (acknowledging trade-offs)  
Use: 🌑 (threat modeling sections)

### Implementation
Primary emoji: 😐 (shipping with awareness)  
Secondary: ✅ (marking progress)  
Sprinkle: 🌑 (documenting failure modes)

### Testing
Primary emoji: 😐 (breaking things with a smile)  
Use: ✅ (coverage milestones)  
Add: 🌑 (edge cases and failure scenarios)

### User-Facing Documentation
Primary emoji: 😐 (keeping it light)  
Minimize: 🌑 (don't terrify users)  
Avoid: Internal persona references

---

## Anti-Patterns (Do Not Use)

**Standard Emoji Prohibited**:
- ❌ No red X (use 🌑 for warnings or just state the problem)
- ✨ No sparkles (Harold doesn't do sparkles)
- 🎉 No celebrations (Harold shipped, but at what cost?)
- 😭 No crying (Harold hides the pain, doesn't show it)
- 🚀 No rockets (shipping is routine, not exciting)
- 💪 No flex (Harold's strength is internal)
- 🔥 No fire (Harold's already burning out)

**When Tempted to Use Standard Emoji**:
1. Ask: "Would Harold use this?"
2. Answer: "No, Harold would smile nervously instead"
3. Use 😐 and describe the feeling in text

---

## Combination Patterns

### Security Warnings
```markdown
🌑 **Dark Harold Warning**: Timing attacks possible if implemented naively.

😐 We'll implement it anyway, but document the attack vectors.
```

### Shipping Decisions
```markdown
✅ Module complete (94% coverage)
😐 Remaining 6% is error handling for edge cases that will definitely happen in production
🌑 Plan accordingly
```

### Architecture Narratives
```markdown
📺 **The Tale of Multi-Model Routing**

😐 In the beginning, there was one model. It was expensive.
🌑 Then there were many models. Routing became the problem.
✅ Now we have tinyclaw. Harold smiles through the complexity.
```

---

## Update Protocol

This reference is a living document. When adding new Harold emoji:

1. **Propose**: Create GitHub issue with emoji candidate and rationale
2. **Validate**: Must represent an aspect of Harold's persona
3. **Document**: Add to this reference with usage guidelines
4. **Sync**: Update CONTRIBUTING.md and relevant documentation

**Approval Required From**:
- harold-documenter (narrative consistency)
- Dark Harold (memetic security audit)
- Hide the Pain Harold himself (does it capture the essence?)

---

## Examples in the Wild

### Good Usage
```markdown
😐 The forward secrecy module is complete. All tests pass.
🌑 Assuming the cryptographic primitives aren't backdoored.
✅ Shipped with 94% coverage.
```

### Bad Usage
```markdown
❌ Tests failed  # Use 🌑 or describe failure
🎉 Feature complete!  # Harold doesn't celebrate, he ships
🚀 Deploying to prod  # It's just Tuesday, not a rocket launch
```

---

## Harold's Approval

*"I've made a career out of hiding pain. Now I'm hiding it in emoji form."* — Harold (probably)

😐 Use this reference wisely. Dark Harold is always watching. 🌑
