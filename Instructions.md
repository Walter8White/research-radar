# Research Radar — Product Development Instructions

## Goal

Research Radar is a local-first tech intelligence app.

It helps users generate a concise morning brief about AI, robotics, infrastructure, startups, open source, regulation, geopolitics, and influential public discussion.

The product must stay simple, useful, and non-overkill.

Core principles:

- Local-first by default.
- Users bring their own API keys.
- No secrets committed.
- No unnecessary cloud backend.
- Reports should be concise, actionable, and readable with morning coffee.
- The app must support both technical signals and strategic signals.
- Each development step must be validated by the user before moving to the next one.

---

## Mandatory Workflow for Codex Agent

For every development task:

1. Read this `Instructions.md`.
2. Inspect the current codebase before editing.
3. Propose a short implementation plan.
4. Make the minimal necessary changes.
5. Run relevant tests or manual checks.
6. Summarize what changed.
7. Ask the user for validation before starting the next task.
8. Update this `Instructions.md` after each completed development step:
   - mark the task status
   - add implementation notes
   - add known issues
   - update the roadmap if priorities changed

Do not silently continue across multiple major features.

After each major task, stop and ask:

> “Do you validate this step before I continue?”

---

## Hard Rules

Never commit or package:

- `.env`
- API keys
- user databases
- personal reports
- local generated data
- build folders
- packaged releases
- private watchlists

Keep ignored:

- `data/*.db`
- `reports/*.md`
- `.env`
- `build/`
- `dist/`
- `release/`
- `*.spec`

Do not hardcode API keys.

Do not require users to use Git.

Do not require terminal usage for the final end-user flow, except for early developer builds.

---

# Ordered Roadmap

## Phase 0 — Stabilize Current Foundation

### Status
TODO

### Goal
Make sure the current Linux packaged app is stable and reproducible.

### Tasks
- Verify local Streamlit UI works.
- Verify packaged Linux build works from a clean extracted folder.
- Verify config files are copied correctly at first launch.
- Verify `.env`, `config`, `data`, and `reports` are local to the extracted app folder.
- Verify OpenAI API key can be entered from UI.
- Verify topics can be edited from UI.
- Verify arXiv and GitHub collectors use UI-configured topics.
- Verify generated report appears in the UI.
- Verify `build_linux.sh` works from scratch.

### Expected Result
A user can download `ResearchRadar-linux.tar.gz`, extract it, run `./ResearchRadar`, paste their own API key, edit topics, and generate a brief.

### Validation With User
Ask the user to test:
- clean extraction
- first launch
- topic editing
- API key saving
- report generation

Stop after this phase.

---

## Phase 1 — Freshness and Recency Control

### Status
TODO

### Goal
Ensure the app only prioritizes recent and current information.

### Problem
Currently, some sources can return older items. The product must avoid surfacing stale papers, old blog posts, and old repos unless explicitly relevant.

### Tasks
- Add recency filtering per source:
  - arXiv: default last 7 or 14 days
  - RSS: default last 7 days
  - GitHub: recently updated or created repositories only
- Add a UI setting:
  - `Last 24h`
  - `Last 3 days`
  - `Last 7 days`
  - `Last 30 days`
- Store user choice locally.
- Make freshness affect scoring.
- Add visible freshness information in the report:
  - published date
  - collected date
  - age in days
- Add fallback behavior when a source has no date.
- Avoid ranking undated items too high.

### Files Likely Involved
- `app.py`
- `core/scoring.py`
- `core/database.py`
- `collectors/arxiv_collector.py`
- `collectors/rss_collector.py`
- `collectors/github_collector.py`
- `core/report.py`

### Expected Result
The brief feels current. Old content does not dominate unless intentionally allowed.

### Validation With User
Show a sample report and confirm that dates and recency look correct.

Stop after this phase.

---

## Phase 2 — Better Scoring and Selection Algorithm

### Status
TODO

### Goal
Improve ranking so the morning brief surfaces only the most important signals.

### Problem
Current scoring is keyword-heavy. It can over-rank generic content and under-rank strategic signals.

### New Scoring Dimensions
Implement separate dimensions:

- `relevance_score`
- `freshness_score`
- `technical_depth_score`
- `strategic_importance_score`
- `market_impact_score`
- `geopolitical_impact_score`
- `source_quality_score`
- `momentum_score`
- `noise_penalty`
- `final_score`

### Selection Rules
The morning brief should not be dominated by one source type.

Add diversity constraints:
- max 2–3 research papers in top brief
- max 2 GitHub repos
- max 2 business/funding items
- max 2 infrastructure/geopolitical items
- allow override if a signal is extremely important

### Ceiling Breaker Detection
Add stronger priority for:
- major model releases
- major acquisitions
- funding above meaningful thresholds
- strategic partnerships
- public statements from influential people
- export controls
- chip/infrastructure shifts
- major open-source releases
- robotics breakthroughs with clear implications

### Expected Result
The top brief should feel curated, not like a sorted RSS dump.

### Validation With User
Generate a report and ask the user:
- Are the top signals actually important?
- Is the report too research-heavy?
- Is the business/geopolitics coverage good enough?
- Is there obvious noise?

Stop after this phase.

---

## Phase 3 — Report Length Levels

### Status
TODO

### Goal
Allow users to choose how long the generated report should be.

### UI Setting
Add report length selector:

1. `Ultra Short`
   - 5 bullets max
   - 1–2 minute read

2. `Short`
   - TL;DR + 3 top signals
   - 3–5 minute read

3. `Standard`
   - TL;DR + 5 top signals + watchlist
   - 5–8 minute read

4. `Deep`
   - more detailed analysis
   - more source items
   - 10–15 minute read

### Tasks
- Add UI selector.
- Store preference locally.
- Pass length setting to LLM prompt.
- Adjust number of displayed raw items.
- Adjust report word budget.
- Ensure non-LLM fallback also respects report length.

### Expected Result
Users can tune report density without editing code.

### Validation With User
Generate reports at all 4 levels and confirm format/length.

Stop after this phase.

---

## Phase 4 — LLM Provider Abstraction

### Status
TODO

### Goal
Make LLM usage optional and provider-independent.

### Providers
Support:

1. OpenAI API
2. Ollama local
3. No LLM fallback

### Tasks
- Create a provider abstraction:
  - `core/llm/providers.py`
  - `OpenAIProvider`
  - `OllamaProvider`
  - `NoLLMProvider`
- Add UI selector:
  - `OpenAI`
  - `Ollama`
  - `Disabled`
- For OpenAI:
  - user provides API key
  - model configurable
- For Ollama:
  - user provides local model name
  - default suggestion: `llama3.1`, `qwen2.5`, or similar
  - app calls local Ollama endpoint
- If no LLM:
  - generate deterministic structured report from scores and summaries
- Add connection test buttons:
  - “Test OpenAI”
  - “Test Ollama”
- Show clear error messages.

### Expected Result
Users who do not want paid API calls can use a local open-source LLM.

### Validation With User
Test:
- OpenAI mode
- disabled mode
- Ollama mode if available

Stop after this phase.

---

## Phase 5 — Automation Agent / Scheduler

### Status
TODO

### Goal
Allow the user to schedule automatic reports on their own computer.

### User Story
The user should be able to choose:
- when the report runs
- where it is saved
- whether to collect fresh sources
- whether to open the report automatically
- whether to notify by local desktop notification

### Tasks
- Add UI section: `Automation`
- Add schedule options:
  - daily
  - weekdays
  - custom time
- Add output folder selector or text field.
- Add button:
  - `Save Automation`
  - `Run Now`
  - `Disable Automation`
- Linux first:
  - create or update a user cron entry
- Later:
  - macOS LaunchAgent
  - Windows Task Scheduler
- Add safe preview of the scheduled command before saving.
- Do not create automation without explicit user action.

### Expected Result
The app can generate a morning brief automatically on the user’s computer.

### Validation With User
On Linux, verify:
- cron entry is created
- report runs at chosen time
- output path works
- disable works

Stop after this phase.

---

## Phase 6 — Twitter / X Source Integration

### Status
TODO

### Goal
Incorporate influential public discussion from Twitter/X.

### Motivation
The product should capture:
- CEO activity
- public statements from important researchers
- conflicts between major tech figures
- regulatory/geopolitical debates
- emerging technical debates
- viral demos with real technical impact

### Important Constraint
Do not scrape aggressively or violate platform rules.

### Preferred Approach
Start with Bring Your Own API / export / manual watchlist.

Possible modes:

1. Manual mode
   - user adds tweet URLs manually
   - app fetches metadata if possible
   - safest MVP

2. Watchlist mode
   - user maintains list of accounts
   - app checks recent posts if API access is configured

3. API mode
   - user provides X/Twitter API token
   - app collects recent posts from watchlisted accounts

4. Alternative social sources
   - Bluesky
   - RSS mirrors
   - official blogs
   - Hacker News
   - Reddit
   - YouTube RSS for robotics demos

### Tasks
- Add `config/social_sources.yaml`.
- Add UI for:
  - accounts to watch
  - people/companies of interest
  - manual post URLs
- Add social collector abstraction.
- Add scoring for social items:
  - source credibility
  - engagement
  - who said it
  - topic relevance
  - strategic importance
  - controversy / conflict signal
- Add source categories:
  - CEO statement
  - researcher comment
  - technical debate
  - policy debate
  - demo
  - conflict / market signal
- Add report section:
  - `People & Public Signals`

### Expected Result
The report can say things like:
- “Yann LeCun argued X; this matters because…”
- “Anthropic CEO said Y; likely implication…”
- “A public conflict around export controls is emerging…”

### Validation With User
Start with manual tweet URL mode before full API.

Stop after this phase.

---

## Phase 7 — Better Source Management

### Status
TODO

### Goal
Let users manage sources from the UI.

### Tasks
- Add UI for RSS feeds:
  - add feed
  - remove feed
  - edit category
  - test feed
- Add UI for source tiers:
  - Tier 1: must-read
  - Tier 2: useful
  - Tier 3: experimental
  - Rejected: too noisy
- Add source quality scoring.
- Track source reliability over time:
  - useful items produced
  - noise rate
  - average score
- Add suggested source additions later.

### Expected Result
Users can customize the radar without editing YAML manually.

### Validation With User
Confirm source editing works in packaged app.

Stop after this phase.

---

## Phase 8 — Desktop App Packaging for Linux, Windows, macOS

### Status
TODO

### Goal
Provide desktop builds for the three main operating systems.

### Current Strategy
Route A:
- Keep Streamlit local app.
- Package with PyInstaller.
- Distribute OS-specific builds.

### Linux
Already started.

Target:
- `.tar.gz`
- later possibly `.AppImage` or `.deb`

### Windows
Build on Windows.
Target:
- `.zip` with `.exe`
- later installer if needed

### macOS
Build on macOS.
Target:
- `.app` bundle or `.zip`
- later `.dmg`

### macOS Complexity
macOS is more complicated because of:
- Gatekeeper warnings
- app signing
- notarization
- permissions
- quarantine flags on downloaded apps

For early versions, unsigned builds are acceptable for testers, but users may need to right-click → Open.

Later, for polished distribution:
- Apple Developer account
- code signing
- notarization
- `.dmg` packaging

### Tasks
- Make code paths OS-independent.
- Move user data to OS-appropriate directories:
  - Linux: `~/.research-radar`
  - macOS: `~/Library/Application Support/ResearchRadar`
  - Windows: `%APPDATA%/ResearchRadar`
- Build scripts:
  - `build_linux.sh`
  - `build_windows.ps1`
  - `build_macos.sh`
- Avoid hardcoded Linux-only paths.
- Test each build from a clean folder.
- Package sample config files.
- Ensure API key is stored locally and not inside the app bundle.

### Expected Result
Users can download and run Research Radar without using Git.

### Validation With User
Validate Linux first, then Windows, then macOS.

Stop after each OS build.

---

## Phase 9 — Website / Landing Page

### Status
TODO

### Goal
Create a public website that explains the project and gives installation/download instructions.

### Content
The site should include:

- What Research Radar is
- Who it is for
- Why it exists
- Screenshots
- Example morning brief
- Download buttons
  - Linux
  - Windows
  - macOS
- Setup instructions
- API key explanation
- Local-first privacy statement
- Roadmap
- GitHub link
- FAQ

### Recommended Implementation
Start simple:
- static site
- GitHub Pages / Vercel / Netlify / Cloudflare Pages

### Important Messaging
Make clear:
- Users use their own API keys.
- Their API key is stored locally.
- Reports and data are local.
- No backend account required.
- Open-source project.

### Expected Result
A user can understand and install the app without reading the source code.

### Validation With User
Ask user to review copy, screenshots, and download flow.

Stop after this phase.

---

# Current Known Issues

Update this section after every development step.

## Known Issues
- Linux packaging works but should be tested from clean extracted folders.
- macOS packaging will require extra work due to Gatekeeper/signing.
- Twitter/X integration likely requires careful API/token handling.
- Current scoring is still evolving.
- Momentum scores require multiple snapshots over time.
- RSS feeds can be malformed but often still parse.
- GitHub unauthenticated API can hit 403 rate limits.

---

# Development Notes

Update this section after every completed phase.

## Notes
- The product should stay lightweight.
- Avoid premature SaaS/backend architecture.
- Prefer local-first packaging.
- Prefer explicit user configuration over hidden automation.
- Keep UI understandable for non-terminal users.
- Keep advanced features optional.

---

# Next Step

Start with **Phase 0 — Stabilize Current Foundation**.

Do not proceed to Phase 1 until the user validates Phase 0.
