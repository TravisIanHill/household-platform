# Development Discovery — Phase 1 Specification

Status: **Proposed** design, October 17, 2026. Nothing here exists yet. Labels: Stated / Verified / Proposed / Interpreted (see DEVELOPER-HANDOFF-MOP.md).

## 1. Goal
Travis describes what he wants to accomplish. The tool finds software, components, implementations and ideas he would not have found by name, shows evidence for each requirement, makes the tradeoffs comparable, and lets him save a decision he can reuse. Phase 1 succeeds on useful discovery and saved evidence; no editor or deployment features.

Headline acceptance test (proposed in conversation, accepted informally by Travis): from "I want to catalog a new Ryobi tool", reach three relevant results within five minutes, see how each handles the workflow, compare them, and save the best ideas.

## 2. The search brief
- Start screen: a large prompt for the intended outcome plus an optional context panel (who will use it, where it runs, constraints).
- The tool produces an **editable brief** that keeps the original wording and separates required capabilities, preferences, exclusions, environment and open questions. The interpretation is shown to the user, not hidden in an expanded query.
- Ask a follow-up question only when the answer would materially change the search; otherwise keep the uncertainty and start.
- Briefs are **versioned**. When a constraint is added, the tool can show why the shortlist changed.
- Distinctions the interpreter must preserve (example, tool registration): storing a photo vs. capturing one on a phone; retaining an existing QR image vs. decoding a QR code; storing a serial number vs. reading it from a label; configurable fields vs. usable by a family member without setup.

## 3. Result roles (each result states one)
- **Application** — something to adopt.
- **Component** — a part to integrate (for example a scanning library); judged only against the part of the workflow it covers.
- **Implementation** — concrete code, schema, route or test showing how a feature is done.
- **Idea to inspect** — an interface or workflow pattern worth studying.
Comparison happens within a role. Applications and small libraries are not ranked against each other.

## 4. Evidence states
- **Documented** — a source describes support.
- **Code located** — an implementation relevant to the claim was found.
- **Tested locally** — a recorded test exercised the behavior in a known environment.
- **Unclear** — evidence is insufficient or ambiguous.
- **Absent or contradicted** — requires evidence of a limitation. "Not found" is never converted to "not supported"; the scope searched is stored.
States are not a ladder. Documentation may describe a newer release than the inspected code; a function name is not proof it is wired to the interface; a feature request or screenshot is not evidence of a shipped backend workflow. Each claim keeps revision, location, observation date, evidence type and limits; saved findings show their age and warn if the source changed.

## 5. Pipeline (Proposed)
1. Interpret the request into an editable brief.
2. Plan searches (qualifiers, synonyms, adjacent terms).
3. Acquire a bounded candidate set from GitHub (no attempt to index everything).
4. Inspect promising candidates: README, docs, file tree, releases, selected source.
5. Assess each requirement into an evidence state.
6. Rank with transparent rules: hard constraints and required capabilities first; unknowns preserved; no single averaged score that hides a missed must-have.
7. Present results and comparison.
8. Save findings.
Model assistance may help steps 1, 2 and 5 but never replaces evidence: a model must not declare support because it recognizes a project name. The tool must work with model assistance off.

## 6. Data model (Proposed)
SearchBrief (revision, original text, interpretation, context); Requirement (name, definition, user wording, synonyms, required/preferred/exclusion, evidence expectation, related); Candidate (repository, role, license, language, archived flag, last activity, revision inspected); CapabilityClaim (candidate, requirement, state, explanation, scope searched, limits); Evidence (type, location, revision, observed date, origin: project / observed in code / inferred / added by Travis); Relationship (kind, source, confidence); SavedFinding (brief revision, candidate, label, reason, notes, evidence snapshot); Comparison; EvaluationRun (mode, job state, partial results, provider limits hit). Acquired source material is stored separately from generated interpretation. Keep links and short references to third-party text; do not store long copies of copyrighted content.

## 7. Results and comparison
- Result row: name, role, purpose, deployment context, requirement coverage, evidence freshness, next action. Popularity is context only.
- Detail panel: requirement, what was found, where, what remains unknown, what to test next; screenshots or examples when available; license; limitations; notes.
- Comparison: rows are the brief's requirements, columns are shortlisted candidates, cells show evidence state with a link. Keep "adopt this application" and "extend our existing app" as separate decision paths.
- Actions: Open evidence, Compare, Save finding, Add note, Mark for test. Phase 1 never downloads, executes or deploys candidate code.
- Interface: Apple-inspired, readable, rounded, persistent navigation, detail pane; keyboard and touch access to everything.

## 8. Saved findings
Labels: Candidate to adopt, Component to investigate, Pattern to learn from, Not suitable for this need, Worth revisiting. Rejections keep the reason ("too complicated for family capture"). Findings also keep who supplied each fact (project, observed, inferred, Travis). Export a readable document with source references plus structured data another assistant can use without the conversation.

## 9. Jobs
States: queued, searching, inspecting, partial, complete, failed, cancelled. Partial evidence survives a provider failure.

## 10. Constraints (Verified Oct 17, 2026, docs.github.com REST search)
1,000 results per search; 10 unauthenticated requests per minute for search; at most 4,000 repositories searched per query; at least one search term for code search; public code search usable unauthenticated per the documentation. Authenticated limits not captured. The adapter treats repository search, code search, file retrieval, authentication, pagination, quotas and failures separately and shows the user when a mode is unavailable instead of simulating it. Private repositories are out of scope for Phase 1. Tokens stay server-side.

## 11. Non-goals for Phase 1
Editor, script runner, Git operations on our repositories, build and deployment tooling, indexing all of GitHub, private repositories, executing candidate code.

## 12. Existing tools reviewed (light scan, Oct 17, 2026; none installed or tested)
- GitDeepSearch: open-source tool that turns plain language into GitHub search qualifiers via the Search API; its own roadmap lists license filters, repo comparison and AI query rewriting as not yet done.
- Quantleaf "GitHub Natural Advanced Search": browser extension translating natural language to search syntax; store listing shows last update March 2021.
- Assista GitHub Search: natural-language repository search with language filter and sorting, inside a larger chat product.
- Exa: commercial search API advertising concept search restricted to a GitHub category (possible optional acquisition source).
- RepoHunt: claims AI natural-language repository search; only a promotional listing found; unverified.
- Greptile: commercial; natural-language questions over repositories you name, with code references (the "prove it works" half, but requires naming the repo first).
- Not reviewed: Sourcegraph, grep.app and similar code-search tools.
Finding: no reviewed tool breaks a request into requirements, verifies each against inspected evidence with stated uncertainty, and keeps comparison and saved findings. A light scan cannot prove none exists; revisit before committing to build.

## 13. Acceptance briefs (Travis judges a small set of useful findings and known mismatches for each)
**Brief 1 — Household tool registration.** Photograph or enter a tool; capture model and serial; attach receipt; record warranty; retain an existing QR image; local hosting; simple for a family member. Observed but not evaluated references: Nestarr (README and API contract read: documents data-tag parsing, QR and barcode scan endpoints, UPC lookup, warranties; MIT; code not read); Homebox, Grocy, Snipe-IT (mentioned in community discussions only).
**Brief 2 — Document review.** Intake, OCR, preview, people links, permissions, duplicate evidence, approval before filing. Paperless-ngx is a named unevaluated reference; Travis wants his own review and storage methodology preserved, so any candidate is judged as Application, Component or Pattern.
For each brief measure time to a useful shortlist and evidence quality, not result count.

## 14. Failure cases that must behave honestly
Weak repository descriptions; unfamiliar vocabulary; partial component solutions; archived or renamed repositories (for example a project that continues under a fork); inaccessible code search; documentation that conflicts with code; queries with nothing suitable. Reporting uncertainty is a success.

## 15. Open decisions
Final name; model provider and local-versus-hosted; first capability vocabulary; Saturn runtime and persistent storage; GitHub token scope and authenticated limits; stack confirmation; optional paid acquisition sources such as Exa; relationship to the household portal.
