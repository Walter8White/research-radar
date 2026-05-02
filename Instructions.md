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
Done

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
Done

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

### Implementation Notes
- Added a local freshness window setting in the Streamlit sidebar:
  - `Last 24h`
  - `Last 3 days`
  - `Last 7 days`
  - `Last 30 days`
- Stored the selected freshness window locally as `RECENCY_WINDOW_DAYS`.
- Added shared freshness helpers for date normalization, age calculation, filtering, and freshness score adjustment.
- Applied recency filtering to arXiv, RSS, GitHub collection, and database report selection.
- Added `freshness_score` and `collected_at` database fields with safe migration for existing local databases.
- Added visible freshness metadata in reports:
  - freshness window
  - published date
  - collected date
  - age labels
- Adjusted report presentation after user review:
  - removed visible freshness score
  - removed visible collection date
  - renamed score to relevance
  - changed momentum display from numeric metric to a word label
  - moved GitHub metrics into a right-side visual block in the Streamlit-rendered report
  - display GitHub growth as `TBD` until enough local snapshot history exists
  - added best-effort GitHub stargazer history lookup for absolute 24h/7d star growth independent of local app history
  - removed `TBD` from report output; missing momentum now appears as `Not tracked` or `Not available yet`
  - added sober emoji accents to report headings and sections
- Generated a sample report at `reports/2026-04-29.md`.

### Known Issues
- Existing database rows are rescored for freshness at report time, but their stored `score` is only refreshed after the item is collected again.
- GitHub fork growth still requires repeated local collections; star growth can use GitHub stargazer history when API quota allows it.
- GitHub stargazer history lookup is capped per collection run to avoid exhausting unauthenticated API limits.
- Runtime checks require the project virtual environment because the system Python may not have `beautifulsoup4` installed.

### Deferred Follow-Ups
- Fix GitHub growth edge cases and stale rows that still lack `github_growth_source`.

---

## Phase 2 — Better Scoring and Selection Algorithm

### Status
Done

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

### Implementation Notes
- Added multidimensional scoring in `core/scoring.py`:
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
- Kept existing `score` field as the final score for backward compatibility.
- Added database columns for all scoring dimensions with safe migrations.
- Updated arXiv, RSS, and GitHub collectors to store scoring dimensions for newly collected items.
- Added top-brief diversity selection:
  - max 2 research papers, with one ceiling-breaker override
  - max 2 GitHub repos, with one ceiling-breaker override
  - max 2 business/startup items
  - max 2 infrastructure/geopolitics items
- Regenerated sample report at `reports/2026-04-29.md`.

### Known Issues
- Existing rows collected before Phase 2 do not have full score dimensions yet; they will update when recollected.
- Current ceiling-breaker detection is keyword-based and will need tuning after user review.
- Business/geopolitics coverage depends heavily on RSS source quality and may still need better feeds.

---

## Phase 3 — Report Length Levels

### Status
Done

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

### Implementation Notes
- Added report length profiles:
  - `Ultra Short`
  - `Short`
  - `Standard`
  - `Deep`
- Added a Streamlit sidebar selector for report length.
- Stored the preference locally as `REPORT_LENGTH`.
- Added CLI support with `--report-length`.
- Passed report length to the LLM prompt.
- Adjusted LLM word budget, TL;DR size, number of top signals, watchlist length, and number of source items per profile.
- Added deterministic non-LLM fallback that respects report length.
- `Ultra Short` now emits only a compact morning brief with up to 5 bullets and no raw source sections.
- `Deep` shows more top items and more raw source items per category.
- Tested all 4 levels from CLI.

### Known Issues
- LLM output can still vary slightly around target word budget, but the strongest structural constraints are enforced in prompt and report assembly.
- All report lengths currently write to the same daily report file, so testing multiple lengths overwrites the previous generated report for that day.

---

## Phase 4 — LLM Provider Abstraction

### Status
Done

### Goal
Make LLM usage optional and provider-independent.

### Providers
Support:

1. OpenAI API
2. Claude API
3. No LLM fallback

### Tasks
- Create a provider abstraction:
  - `core/llm/providers.py`
  - `OpenAIProvider`
  - `ClaudeProvider`
  - `NoLLMProvider`
- Add UI selector:
  - `OpenAI`
  - `Claude`
  - `Disabled`
- For OpenAI:
  - user provides API key
  - model configurable
- For Claude:
  - user provides API key
  - model configurable
- If no LLM:
  - generate deterministic structured report from scores and summaries
- Keep LLM settings simple:
  - provider selector
  - provider-specific API key and model fields
  - one `Save LLM` button with confirmation

### Expected Result
Users can choose OpenAI, Claude, or a deterministic no-LLM fallback.

### Validation With User
Test:
- OpenAI mode
- Claude mode
- disabled mode

Stop after this phase.

### Implementation Notes
- Added provider abstraction in `core/llm/providers.py`.
- Added providers:
  - `OpenAIProvider`
  - `ClaudeProvider`
  - `NoLLMProvider`
- Added UI provider selector:
  - `OpenAI`
  - `Claude`
  - `Disabled`
- Added local settings for:
  - `LLM_PROVIDER`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `ANTHROPIC_API_KEY`
  - `CLAUDE_MODEL`
- Simplified LLM settings UI:
  - provider selector is shown first
  - API key and model fields appear only for the selected provider
  - removed separate test/disable buttons
  - `Disabled` is selected from the provider menu
  - one `Save LLM` button persists settings and shows confirmation
- Updated report generation to use the selected provider.
- Kept deterministic fallback for disabled provider or provider failures.
- Made disabled-mode output explicit:
  - report header now shows `LLM mode`
  - fallback section is labeled `Rule-Based Brief (LLM Disabled)`
  - fallback wording uses source excerpts instead of LLM-like “why it matters” language
- LLM provider selection is now read fresh from local `.env` at generation time, so toggling provider in Streamlit does not rely on stale process environment values.
- LLM-generated sections are labeled `LLM Brief`; disabled-mode sections are labeled `Rule-Based Brief (LLM Disabled)`.
- Detail sections now show `Source digest` snippets instead of raw signal dumps:
  - papers prioritize contribution/method/result sentences from the abstract
  - RSS and GitHub items show short cleaned source digests
  - GitHub numeric metadata stays in the dedicated metrics block
- Updated `.env.example` with provider settings.
- Removed Ollama support after product decision to keep Phase 4 focused on OpenAI, Claude, and no-LLM fallback.

### Known Issues
- Claude and OpenAI calls happen during report generation when those providers are selected.
- Provider failures fall back to deterministic report text and include the provider error in the generated report.

---

## Phase 5 — Automation Agent / Scheduler

### Status
Done

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

### Implementation Notes
- Added Linux-first automation support through user cron.
- Added `core/automation.py`:
  - builds safe cron command previews
  - installs a marked `Research Radar` crontab block
  - removes only the marked `Research Radar` block when disabling automation
- Added Streamlit `Automation` section:
  - schedule: `Daily` or `Weekdays`
  - custom 24h run time
  - output folder
  - collect fresh sources toggle
  - open report automatically toggle
  - desktop notification toggle
  - safe scheduled command preview
  - `Save Automation`
  - `Run Now`
  - `Disable Automation`
- Cron entries include available desktop environment variables (`DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`) so `notify-send` has a better chance of working from cron.
- Added CLI options:
  - `--output-dir`
  - `--open-report`
  - `--notify`
- `Run Now` uses the automation settings without writing cron.
- Added `.env.example` defaults for automation preferences.

### Known Issues
- Linux cron only for Phase 5.
- `notify-send` is required for desktop notifications.
- Desktop notifications from cron depend on the active Linux session exposing notification bus variables when automation is saved.
- `xdg-open` is required for automatic report opening.
- Cron runs in the project directory and logs to `data/automation.log`.

---

## Phase 6 — Twitter / X Source Integration

### Status
Implemented — awaiting user validation

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
Start with Bring Your Own API and automatic recent search from the user's configured topics, companies, people, and optional account watchlist.

Possible later modes:

1. Alternative social sources
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
Start with automatic X recent search using user-provided X API bearer token.

Stop after this phase.

### Implementation Notes
- Added `config/social_sources.yaml`.
- Added official X API recent-search collector in `collectors/social_collector.py`.
- The X query is built automatically from:
  - `focus_topics`
  - `companies_focus`
  - `people_focus`
  - optional account watchlist in `config/social_sources.yaml`
- Added `X_BEARER_TOKEN` local setting in `.env.example` and Streamlit UI.
- Added `Public Signals` sidebar section:
  - X API bearer token
  - optional account watchlist
  - max X posts per run
  - enable/disable X collection
- Added `Social` collector to `collect_all`.
- Added report category:
  - `People & Public Signals`
- Added scoring support for `people_public_signals` / `x_api`.
- Uses official X API endpoint only; no browser scraping.

### Known Issues
- X recent search requires the user's own X API access and bearer token.
- X API tiers and limits may prevent recent search depending on the user's account.
- The current collector runs one bounded query per collection run and does not paginate.
- Query length is capped conservatively, so very long topic/company/people lists may be truncated.

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
- Existing database rows receive report-time freshness recalculation until they are collected again.
- Existing rows collected before Phase 2 do not have full score dimensions until recollected.
- Phase 1 follow-ups remain: fix GitHub growth edge cases and research paper raw signals.
- Report length tests overwrite the same daily markdown file.

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
- Phase 1 added recency controls and report-visible freshness without adding a cloud backend or requiring accounts.
- Phase 2 added multidimensional scoring and diversified top-brief selection while keeping the app local-first.
- Phase 3 added report density controls with LLM and non-LLM support.
- Phase 4 added provider abstraction for OpenAI, Claude, and disabled/no-LLM mode.
- Phase 4 originally explored Ollama, then removed it to keep provider choices simpler and avoid local server/cloud-free-tier ambiguity.
- Phase 5 added Linux cron automation with explicit preview and user-triggered save/disable actions.
- Phase 6 added automatic X recent-search collection from user topics, companies, people, and optional watched accounts.
- Improved sidebar focus settings wording:
  - `Priority topics` became `What to track closely`
  - `Negative topics` became `What to avoid`
  - `Domain keywords` became `Signal groups`
  - removed the confusing reload topics button
  - made focus and matching-term text areas taller
  - clarified that matching terms classify/rank items and are complementary to focus topics
- Simplified the user-facing focus model:
  - users now configure as many focus topics as they want
  - users first save the topic list
  - each saved focus topic then gets a priority menu: `Critical`, `High`, `Medium`, or `Low`
  - priorities are saved separately with `Save priorities`
  - users still configure a simple `What to avoid` list
  - added placeholder lists for companies focus and people focus
  - signal-group keywords remain internal backend configuration, hidden from the main UI
  - backend collection and scoring now read the new `focus_topics` structure with fallback to legacy `priority_topics`
  - collectors no longer use hidden signal-group keywords as search queries; arXiv and GitHub collection now starts from user-saved topics only

---

# Next Step

Validate **Phase 4** with the user.

Do not proceed to Phase 5 until the user validates Phase 4.
