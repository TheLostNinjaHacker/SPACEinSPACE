# Agent entry point

**Before doing anything in this repository, read:**

## [TASKLIST.md](TASKLIST.md)

Then verify claims against [docs/TRUTH-STATUS.md](docs/TRUTH-STATUS.md).

Use task IDs (`T-###`) in commits. Update TASKLIST when work starts or finishes.

**Agent routing & cost:** [docs/AGENT-STACK.md](docs/AGENT-STACK.md) — OpenCode/FreeBuff (free) · Cursor ($20/mo) · HyperAgent (premium) · Ollama 4096-dim local · OpenRouter ad-hoc.

**New use-case?** Append to [docs/USE-CASE-REGISTRY.md](docs/USE-CASE-REGISTRY.md) — every agent, every session. One row, next `UC-###`.

---

## Agent team

| Agent | @name | Roll | Skill |
|-------|-------|------|-------|
| **Orchestrator** | `@orchestrator` | Teamledare — planerar, delegerar, följer upp | `.cursor/skills/orchestrator/SKILL.md` |
| **Blender Artist** | `@blender-artist` | 3D-modellering, material, scener via blender-mcp | `.cursor/skills/blender-artist/SKILL.md` |
| **iOS Engineer** | `@ios-engineer` | Swift/ARKit Pocket-appen | `.cursor/skills/supersenses-ios/SKILL.md` |
| **Film Producer** | `@film-producer` | Investerarfilmen T-005 | `.cursor/skills/film-producer/SKILL.md` |
| **Hantverkare** | `@hantverkare` | Rekrytering & intervjuer (svenska) | `.cursor/skills/hantverkare/SKILL.md` |

Subagents anropas med `@agentnamn` i meddelandet, eller via Task tool från Orchestrator.

### Coordination protocol

1. **Läs TASKLIST.md** — kolla aktiva tasks, plocka en ledig
2. **Sätt `in_progress`** i TASKLIST innan du börjar
3. **Jobba** — använd din skill, om du fastnar, kalla in rätt agent
4. **Vid klar** — uppdatera TASKLIST, beskriv vad som gjordes
5. **Vid blockering** — lämna task `blocked` med orsak, eskalera till Per om det är P0
6. **Ny use-case?** — UC-registret, en rad, nästa `UC-###`

### Git-regler

- Commit-format: `TASKLIST: T-### — vad som gjordes`
- Ingen force-push till main
- Kör CI-checkar innan push: `./scripts/ios-build.sh` för iOS, `pytest` för Python

---

## Film (T-005)

**Shooting manus:** [00-MANUS-V2.md](assets/filmgen/prompts/00-MANUS-V2.md). Meta **v7.1:** [00-META-V7.1-STORYBOARD.md](assets/filmgen/prompts/00-META-V7.1-STORYBOARD.md). Pool/wonder: [00-SCENES-PLOTS-v2.md](assets/filmgen/prompts/00-SCENES-PLOTS-v2.md) · [00-FRAME-INDEX.md](assets/filmgen/prompts/00-FRAME-INDEX.md). **EN + locales:** [00-LANGUAGE-AND-LOCALE.md](assets/filmgen/prompts/00-LANGUAGE-AND-LOCALE.md). Physics: [`.cursor/skills/filmgen-physics/SKILL.md`](.cursor/skills/filmgen-physics/SKILL.md). AR fields: [00-AR-FIELDS-AND-POTENTIAL.md](assets/filmgen/prompts/00-AR-FIELDS-AND-POTENTIAL.md). Cut: [00-CUT-ORDER-2MIN.md](assets/filmgen/prompts/00-CUT-ORDER-2MIN.md). Lessons: [00-FRAME-REVIEW-LESSONS.md](assets/filmgen/prompts/00-FRAME-REVIEW-LESSONS.md). **i2v gotchas (four laws):** [00-FILM-GOTCHAS-T005.md](assets/filmgen/prompts/00-FILM-GOTCHAS-T005.md). Pre-frame cards: [00-PREFRAME-CARDS.md](assets/filmgen/prompts/00-PREFRAME-CARDS.md). HyperAgent↔Cursor bus: [AGENT-SYNC.md](assets/filmgen/AGENT-SYNC.md). Session retro: [HYPERCHAT.md](HYPERCHAT.md). Closer: [00-SPECTRUM-CLOSER.md](assets/filmgen/prompts/00-SPECTRUM-CLOSER.md).  
**Investor lock:** Meeting = **today + potential**. Film (T-005) = leap / funded vision; live Pocket (T-004) = full "what we already have" (don't skip — he underestimates it). Brief: [DEMO-FILM-CREATIVE-BRIEF.md](docs/DEMO-FILM-CREATIVE-BRIEF.md).

---

## iOS (SuperSenses Pocket)

**Skill:** [`.cursor/skills/supersenses-ios/SKILL.md`](.cursor/skills/supersenses-ios/SKILL.md)  
**Setup:** [docs/IOS-DEV-SETUP.md](docs/IOS-DEV-SETUP.md)

**Swift companion skills** (Paul Hudson / [swift-agent-skills](https://github.com/twostraws/swift-agent-skills) catalog):

| Skill | When to use |
|-------|-------------|
| `swiftui-pro` | SwiftUI reviews, modern APIs, performance |
| `swift-concurrency-pro` | async/await, actors, MainActor correctness |
| `swift-testing-pro` | Swift Testing (not XCTest-only) |
| `swiftdata-pro` | SwiftData models / queries (if used) |

### Build & test (prefer MCP over shell)

- **Xcode must be open** with `ios/SuperSensesAR.xcodeproj` for `xcode-tools` MCP.
- Compile: `BuildProject` (not raw `xcodebuild` unless MCP unavailable).
- Tests: `RunAllTests` / `RunSomeTests`.
- SwiftUI: `RenderPreview` for visual verification.
- Apple APIs: `DocumentationSearch` (Xcode MCP) or **Sosumi MCP** — never guess ARKit/RealityKit APIs.
- Terminal fallback: `./scripts/ios-build.sh` (uses xcbeautify).

### Device-only sensors

LiDAR, UWB, magnetometer demo, mic/sound — require **physical iPhone 13 Pro+**. Simulator builds do not validate investor demo acts.

### TRUTH labels

Every sensor layer: **Live / Proxy / Simulated / Partial**. See [docs/TRUTH-STATUS.md](docs/TRUTH-STATUS.md). Never claim thermal camera, WiFi site survey, or probe-grade EMF on phone alone.

---

## Database

Project Postgres is **Supabase** (`supabase/`). Do **not** add Neon/other hosted Postgres unless Per asks.

---

## Autonomous sessions

No specific task ID: follow [research/autoresearch/program.md](research/autoresearch/program.md) — one bounded experiment per iteration, score against [metrics.md](research/autoresearch/metrics.md), log to `experiments/`.

## Blender

Blender MCP addon kräver Blender GUI öppet → tryck N → fliken BlenderMCP → "Connect to MCP server". Port 9876.
# Agent entry point

**Before doing anything in this repository, read:**

## [TASKLIST.md](TASKLIST.md)

Then verify claims against [docs/TRUTH-STATUS.md](docs/TRUTH-STATUS.md).

Use task IDs (`T-###`) in commits. Update TASKLIST when work starts or finishes.

**Agent routing & cost:** [docs/AGENT-STACK.md](docs/AGENT-STACK.md) — OpenCode/FreeBuff (free) · Cursor ($20/mo) · HyperAgent (premium) · Ollama 4096-dim local · OpenRouter ad-hoc.

**New use-case?** Append to [docs/USE-CASE-REGISTRY.md](docs/USE-CASE-REGISTRY.md) — every agent, every session. One row, next `UC-###`.

**Film (T-005):** **Shooting manus:** [00-MANUS-V2.md](assets/filmgen/prompts/00-MANUS-V2.md). Meta **v7.1:** [00-META-V7.1-STORYBOARD.md](assets/filmgen/prompts/00-META-V7.1-STORYBOARD.md). Pool/wonder: [00-SCENES-PLOTS-v2.md](assets/filmgen/prompts/00-SCENES-PLOTS-v2.md) · [00-FRAME-INDEX.md](assets/filmgen/prompts/00-FRAME-INDEX.md). **EN + locales:** [00-LANGUAGE-AND-LOCALE.md](assets/filmgen/prompts/00-LANGUAGE-AND-LOCALE.md). Physics: [`.cursor/skills/filmgen-physics/SKILL.md`](.cursor/skills/filmgen-physics/SKILL.md). AR fields: [00-AR-FIELDS-AND-POTENTIAL.md](assets/filmgen/prompts/00-AR-FIELDS-AND-POTENTIAL.md). Cut: [00-CUT-ORDER-2MIN.md](assets/filmgen/prompts/00-CUT-ORDER-2MIN.md). Lessons: [00-FRAME-REVIEW-LESSONS.md](assets/filmgen/prompts/00-FRAME-REVIEW-LESSONS.md). **i2v gotchas (four laws):** [00-FILM-GOTCHAS-T005.md](assets/filmgen/prompts/00-FILM-GOTCHAS-T005.md). Pre-frame cards: [00-PREFRAME-CARDS.md](assets/filmgen/prompts/00-PREFRAME-CARDS.md). HyperAgent↔Cursor bus: [AGENT-SYNC.md](assets/filmgen/AGENT-SYNC.md). Session retro: [HYPERCHAT.md](HYPERCHAT.md). Closer: [00-SPECTRUM-CLOSER.md](assets/filmgen/prompts/00-SPECTRUM-CLOSER.md).  
**Investor lock:** Meeting = **today + potential**. Film (T-005) = leap / funded vision; live Pocket (T-004) = full “what we already have” (don’t skip — he underestimates it). Brief: [DEMO-FILM-CREATIVE-BRIEF.md](docs/DEMO-FILM-CREATIVE-BRIEF.md).

**Database:** Project Postgres is **Supabase** (`supabase/`). Do **not** add Neon/other hosted Postgres unless Per asks.

**Autonomous sessions** (no specific task ID): follow [research/autoresearch/program.md](research/autoresearch/program.md) — one bounded experiment per iteration, score against [metrics.md](research/autoresearch/metrics.md), log to `experiments/`.

---

## iOS (SuperSenses Pocket)

**Skill:** [`.cursor/skills/supersenses-ios/SKILL.md`](.cursor/skills/supersenses-ios/SKILL.md)  
**Setup:** [docs/IOS-DEV-SETUP.md](docs/IOS-DEV-SETUP.md)

**Swift companion skills** (Paul Hudson / [swift-agent-skills](https://github.com/twostraws/swift-agent-skills) catalog — installed in `~/.cursor/skills/`):

| Skill | When to use |
|-------|-------------|
| `swiftui-pro` | SwiftUI reviews, modern APIs, performance |
| `swift-concurrency-pro` | async/await, actors, MainActor correctness |
| `swift-testing-pro` | Swift Testing (not XCTest-only) |
| `swiftdata-pro` | SwiftData models / queries (if used) |

Index of more community skills: [`.agents/swift-agent-skills-INDEX.md`](.agents/swift-agent-skills-INDEX.md)

### Build & test (prefer MCP over shell)

- **Xcode must be open** with `ios/SuperSensesAR.xcodeproj` for `xcode-tools` MCP.
- Compile: `BuildProject` (not raw `xcodebuild` unless MCP unavailable).
- Tests: `RunAllTests` / `RunSomeTests`.
- SwiftUI: `RenderPreview` for visual verification.
- Apple APIs: `DocumentationSearch` (Xcode MCP) or **Sosumi MCP** — never guess ARKit/RealityKit APIs.
- Terminal fallback: `./scripts/ios-build.sh` (uses xcbeautify).

### Device-only sensors

LiDAR, UWB, magnetometer demo, mic/sound — require **physical iPhone 13 Pro+**. Simulator builds do not validate investor demo acts.

### TRUTH labels

Every sensor layer: **Live / Proxy / Simulated / Partial**. See [docs/TRUTH-STATUS.md](docs/TRUTH-STATUS.md). Never claim thermal camera, WiFi site survey, or probe-grade EMF on phone alone.
