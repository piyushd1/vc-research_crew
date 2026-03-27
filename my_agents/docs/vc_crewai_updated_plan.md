# India-First VC Multi-Workflow CrewAI System — Updated Plan

> **Revision notes**: This is a gap-filled and extended version of the original plan. All original decisions are preserved. Additions are marked **[NEW]** and changes are marked **[CHANGED]**. Everything unmarked was already in the original plan and remains unchanged. A third pass added **[GAP-FIX]** annotations addressing 4 implementation gaps: resume controller logic, explicit checkpoint positions, `one_pager` self-containment, and `downstream_flags` injection mechanics.

---

## Summary

Build a CLI-driven VC research system with 3 top-level workflows: `sourcing`, `due_diligence`, and `portfolio`. Each workflow uses a shared orchestrator plus relevant specialist agents. Final output is selectable per run as `ic_memo`, `full_report`, or `one_pager`. **[CHANGED: renamed from `memo_scorecard`, `narrative`, `dashboard` — see Output Profiles section.]**

The system is India-first by default: English report style, INR/regulatory context, India-prioritized source packs, and pluggable adapters for both open-web and future paid/private data sources. OpenRouter is the default LLM path with a single model tier across all agents for v1. Private uploads are allowed with explicit source tagging and redaction controls. Post-run, the system creates a Linear issue per company and exports a PDF of the report in addition to file output. **[CHANGED: added Linear + PDF outputs.]**

---

## Key Changes

### Interfaces

- Replace the demo-only `main.py` flow with a real CLI contract:
  - `--workflow {sourcing|due_diligence|portfolio}`
  - `--brief path/to/brief.yaml|json`
  - `--output-profile {ic_memo|full_report|one_pager}` **[CHANGED: renamed profiles]**
  - `--approve-mode {auto|manual}` **[NEW: controls human-in-the-loop checkpoints]**
  - optional overrides: `--sector`, `--stage`, `--geography`, `--docs-dir`, `--sources-profile`

- Define a normalized brief schema with these required/optional fields:
  - `company_name`, `website`, `sector`, `stage`, `geography`
  - optional: `one_line`, `investment_thesis`, `questions`, `docs_dir`, `notes`

- Standardize specialist outputs into a structured finding record:
  - `claim`, `evidence_summary`, `source_ref`, `source_type`, `confidence`, `risk_level`, `open_questions`

- **[NEW]** Add an `inter_agent_context` field to every specialist finding record:
  - `downstream_flags`: a list of structured flags the specialist wants to surface to the next agent in the chain (e.g., `{"flag": "revenue_gap", "for_agent": "risk_red_team_analyst", "detail": "..."}`)
  - **[GAP-FIX] Injection mechanics — exactly how the controller uses these flags:**
    1. After each specialist task completes and its Pydantic output is written to `findings/{agent_name}.json`, the Python controller reads the `downstream_flags` list from that JSON.
    2. It filters flags where `for_agent` matches the name of the **next** agent in the execution queue.
    3. It constructs an `injected_context` string from those flags and prepends it to that next agent's task `description` field before the CrewAI task object is instantiated. Example prepend: `"Prior agent flagged the following for your attention:\n- revenue_gap: [detail]\n\nYour task: ..."`.
    4. Flags addressed to agents further downstream (not the immediate next agent) are held in a `pending_flags` dict in `run_state.json` and injected at the point that agent is activated.
    5. No agent ever receives flags not addressed to it. The full injection history is auditable via `run_state.json`.

- Persist run artifacts under a **versioned** output folder per company/workflow: **[CHANGED: added timestamp versioning]**
  ```
  runs/
    {company_slug}/
      {YYYY-MM-DD_HHMMSS}/
        report.md
        report.pdf          ← [NEW]
        scorecard.json
        sources.json
        one_pager.html      ← [NEW: only when --output-profile one_pager]
        run_state.json      ← [NEW: checkpoint resume state]
        findings/
          {agent_name}.json ← intermediate specialist findings for auditability
  ```
  - `latest/` symlink always points to the most recent run for a given company. **[NEW]**
  - Running DD on the same company in week 3 does not overwrite week 1. Both runs are preserved and diffable. **[NEW]**

---

### Output Profiles **[CHANGED + EXTENDED]**

Three output profiles are selectable on every run. All three draw from the same underlying finding records — the difference is the renderer, not the agent work.

| Profile | Format | Length | Purpose |
|---|---|---|---|
| `ic_memo` | Markdown → PDF | 1–2 pages | Quick IC triage: verdict, score, top 3 risks, top 3 reasons to invest/pass |
| `full_report` | Markdown → PDF | Full length | All DD sections, cited evidence, financials, regulatory, founder analysis |
| `one_pager` | Static HTML | Single page | Scannable visual snapshot: traffic-light scores, key metrics, open questions. Shareable with co-investors. |

**[NEW] Renderer architecture:**
- The `report_synthesizer` agent produces a structured intermediate output (`findings_bundle.json`) containing all section data, scores, citations, and gaps.
- A **deterministic, non-LLM renderer** (`src/my_agents/renderers/`) then templates this bundle into the requested format. This is code, not an agent task.
- Three renderer modules: `ic_memo_renderer.py`, `full_report_renderer.py`, `one_pager_renderer.py`.
- PDF generation for `ic_memo` and `full_report`: use `weasyprint` (Python, no headless browser dependency). The `one_pager` HTML is rendered separately and not auto-converted to PDF.
- **[GAP-FIX] `one_pager` self-containment requirement:** The `one_pager_renderer.py` must produce a **fully self-contained single HTML file** with zero external dependencies. Specifically:
  - All CSS is inlined in a `<style>` block within the file — no external stylesheet links.
  - All fonts are either system fonts or base64-encoded and embedded directly in the CSS `@font-face` declaration.
  - No JavaScript CDN links. Any JS used (e.g., for traffic-light colour logic) must be inline in a `<script>` block.
  - No external images. Any icons or visual elements use inline SVG.
  - The rendered file must open correctly in a browser with no internet connection and must be safe to attach to an email without broken references.

---

### Orchestration and Agents

- Use a hierarchical CrewAI design with a custom orchestrator/IC-chief-of-staff manager as the only top-level coordinator.

- Add 3 shared control agents:
  - `orchestrator`
  - `evidence_auditor`
  - `report_synthesizer`

- Add workflow-specific specialist pools and only activate the relevant pool per run.

**[NEW] Human-in-the-loop checkpoint architecture:**
- Checkpoint tasks are defined at the workflow level in `config/workflows/{workflow}.yaml` with a `checkpoint: true` flag.
- When `--approve-mode manual`, the system pauses at each checkpoint, prints a summary of findings so far to the terminal, and prompts: `[APPROVE / SKIP / ABORT]`.
- When `--approve-mode auto`, all checkpoints are silently approved and execution continues.

- **[GAP-FIX] Exact checkpoint positions, pinned per workflow:**

  **`sourcing` workflow** — 1 checkpoint:
  ```yaml
  # config/workflows/sourcing.yaml
  tasks:
    - agent: startup_sourcer
    - agent: thesis_fit_analyst
      checkpoint: true          # PAUSE: review thesis fit score before committing to full scan
    - agent: market_mapper
    - agent: founder_signal_analyst
    # final shortlist produced by report_synthesizer after this
  ```

  **`due_diligence` workflow** — 2 checkpoints:
  ```yaml
  # config/workflows/due_diligence.yaml
  tasks:
    - agent: financial_researcher
    - agent: marketing_gtm_researcher
    - agent: product_tech_researcher
    - agent: customer_competition_analyst
      checkpoint: true          # PAUSE 1: review market/product picture before deep financial + legal work
    - agent: investment_analyst
    - agent: india_regulatory_legal_analyst
    - agent: risk_red_team_analyst
    - agent: valuation_scenarios_analyst
      checkpoint: true          # PAUSE 2: review full findings assembly before IC memo synthesis
    # report_synthesizer runs after final approval
  ```

  **`portfolio` workflow** — 1 checkpoint:
  ```yaml
  # config/workflows/portfolio.yaml
  tasks:
    - agent: portfolio_monitor
    - agent: kpi_burn_analyst
      checkpoint: true          # PAUSE: review KPI/runway picture before recommendations are drafted
    - agent: growth_ops_analyst
    - agent: risk_alert_analyst
    # report_synthesizer runs after this
  ```

  The checkpoint position in each YAML is the **last agent before a phase boundary** — i.e., before the work shifts from data-gathering to synthesis, or from shallow scan to deep diligence. This ensures the human reviews gathered evidence, not half-formed conclusions.

**[NEW] Checkpoint resume / state persistence:**
- Before each agent task executes, the orchestrator writes `run_state.json` with:
  - `completed_agents`: list of agent names + completion timestamps
  - `pending_agents`: remaining queue
  - `findings`: all completed specialist outputs so far
  - `pending_flags`: downstream flags waiting for agents not yet activated
- Re-run detection uses the `--resume {run_folder_path}` CLI flag to target a specific partial run explicitly.

- **[GAP-FIX] Resume controller logic — step by step:**
  1. When `--resume {run_folder_path}` is passed, the controller loads `run_state.json` from that folder before doing anything else.
  2. It reads `completed_agents` and diffs it against the full ordered task queue for the workflow.
  3. Agents in `completed_agents` are instantiated as **no-op stubs** — their prior `findings/{agent_name}.json` output is loaded directly into the evidence registry and findings bundle as if they had just run. No LLM call is made for them.
  4. `pending_flags` from `run_state.json` is re-loaded into the controller's in-memory flag queue so downstream injection continues correctly.
  5. Execution resumes from the first agent **not** in `completed_agents`, with full prior context available.
  6. The resumed run writes all new outputs into the **same timestamped folder** as the original partial run — it does not create a new timestamp folder. The `latest/` symlink is updated only on full completion.
  7. If `--resume` is passed but no `run_state.json` exists in that folder, the controller exits with a clear error: `"No run_state.json found in {path}. Use --brief to start a fresh run."`

For `sourcing`:
- `startup_sourcer`
- `thesis_fit_analyst`
- `market_mapper`
- `founder_signal_analyst` **[see data sources section below]**

For `due_diligence`:
- `financial_researcher`
- `marketing_gtm_researcher`
- `investment_analyst`
- `product_tech_researcher`
- `customer_competition_analyst`
- `india_regulatory_legal_analyst`
- `risk_red_team_analyst`
- `valuation_scenarios_analyst`

For `portfolio`:
- `portfolio_monitor`
- `kpi_burn_analyst`
- `growth_ops_analyst`
- `risk_alert_analyst`

- Keep "full VC org" roles such as LP relations, brand/comms, talent, and back-office as extension stubs in config, but do not make them active execution agents in v1.

---

### Workflow Design

- Add a common ingestion layer before every workflow:
  - normalize company brief
  - ingest optional files/docs
  - collect public-web sources
  - build an evidence registry with trust/recency/source-type tags

**[NEW] Evidence registry conflict resolution:**
- When two sources contradict each other on the same factual claim (e.g., MCA filing shows incorporation date X, founder deck says Y), the registry applies a priority hierarchy:
  1. Government/regulatory filings (MCA, SEBI, RBI, NCLT) — highest trust
  2. Audited financials
  3. Company-provided documents (uploaded private)
  4. Reputable media (ET, Mint, Inc42, Entrackr)
  5. Unverified web / press releases — lowest trust
- Contradictions between tiers 1–2 vs. tiers 3–5 are auto-flagged as `conflict: HIGH` in the finding record and surfaced as open questions in the final report.
- Contradictions within the same tier are flagged as `conflict: MEDIUM` and passed to the `evidence_auditor`.
- The `evidence_auditor` cannot resolve conflicts — it can only escalate them as explicit gaps that must appear in the final report.

`sourcing` workflow:
- thesis match
- market/company scan
- founder and momentum signals
- shortlist recommendation with sourcing score

`due_diligence` workflow:
- company snapshot
- market/GTM analysis
- financial and unit economics review
- product/tech assessment
- India regulatory/compliance review
- risk/red-team challenge
- investment case and final IC memo

`portfolio` workflow:
- KPI and runway review
- market/competitive changes
- regulatory/risk watch
- support recommendations and next actions

- Require the `evidence_auditor` to reject or flag outputs with uncited major claims, unresolved contradictions, or missing high-priority diligence sections.

---

### Founder Signal Analyst — Grounded Data Sources **[NEW]**

LinkedIn scraping is not viable (rate-limited, ToS). The `founder_signal_analyst` must rely on a defined fallback hierarchy instead:

1. **MCA/ROC filings** — director identification, other directorships, company history, past ventures
2. **IP India** — patent filings under founder name (signals technical depth)
3. **SEBI/BSE/NSE disclosures** — if founder has listed-company experience or directorships
4. **Startup India / DPIIT** — DPIIT recognition, government scheme participation
5. **Public press and media** — Inc42, YourStory, ET Startup, Entrackr, The Ken
6. **GitHub** — public repository activity if the founder is technical (signals execution, recency of coding)
7. **Google Scholar / Semantic Scholar** — academic background signals for deep-tech founders
8. **Court records** — NCLT/IBC/public legal databases for prior insolvency or litigation flags

The agent must explicitly state in its finding record which sources it was able to access and which returned no signal. "No signal found" on MCA is itself a signal worth flagging.

---

### Scorecard — Default Weights and Normalization **[NEW]**

The plan specifies that scorecard weights are config-driven but ships no defaults. v1 must include a shipped baseline so the scorecard is usable out of the box.

**Default generalist India scorecard (weights sum to 100):**

| Dimension | Default Weight |
|---|---|
| Market size and growth | 20 |
| Founder quality and signal | 20 |
| Business model and unit economics | 20 |
| Product / tech differentiation | 15 |
| India regulatory / compliance posture | 10 |
| GTM traction and momentum | 10 |
| Risk profile (red team) | 5 |

**Normalization rules:**
- Each dimension is scored 1–5 by the relevant specialist agent.
- Final scorecard score = weighted average × 20 (to yield a 0–100 output score).
- Sector overlays can shift weights (e.g., fintech raises regulatory weight to 20, drops GTM to 5) but weights must always sum to 100. A config validator enforces this at load time.
- A score below 50 auto-generates a `PASS` recommendation. Above 75 generates a `STRONG INTEREST` flag. 50–75 is `CONDITIONAL` with open questions surfaced.

---

### LLM Configuration **[CHANGED]**

- Single model for all agents in v1 (simpler, consistent behavior).
- Model is configured once in `config/llm.yaml`:
  ```yaml
  provider: openrouter
  model: anthropic/claude-3.5-sonnet   # or whichever model is preferred
  temperature: 0.2                      # low temp for research/analysis tasks
  max_tokens: 4096
  ```
- Per-agent model overrides are supported in the YAML schema but not required in v1. The config validator warns if a per-agent override is set without a valid OpenRouter model string.
- Temperature is intentionally low across all agents to minimize hallucination in research/citation tasks.

---

### Post-Run Integrations **[NEW]**

**PDF export:**
- Both `ic_memo` and `full_report` are rendered to PDF automatically after every run using `weasyprint`.
- PDF is saved as `report.pdf` in the run folder alongside `report.md`.
- The `one_pager` HTML is not auto-converted to PDF (it's designed to be opened in browser/shared directly).

**Linear integration:**
- After every completed run, the system creates a Linear issue in a designated VC Research project.
- Issue contains: company name, workflow type, output profile used, run date, scorecard score (if DD), top 3 risks, top 3 signals, and a link to the run folder path.
- Linear project and team IDs are configured in `config/integrations.yaml`.
- Linear push is skipped if `LINEAR_API_KEY` is not set in environment — not a hard failure.
- Implementation: `src/my_agents/integrations/linear_push.py` — called as a post-run hook, not an agent task.

---

### India-First Sources and Tools

- Default search tool: `SerperDevTool`.
- Keep a provider abstraction so `TavilySearchTool` or other search providers can be swapped without changing prompts.
- Use file/PDF/CSV and website ingestion for decks, notes, financial statements, cap tables, and company websites.
- Add custom tools/source adapters in `src/my_agents/tools/` for India-relevant source packs and normalization, with priority given to:
  - MCA/company and director information
  - Startup India/DPIIT references
  - SEBI, NSE, and BSE filings for listed comps and disclosures
  - RBI and sector-regulator material where relevant
  - CCI/NCLT/IBC/public legal risk references
  - IP India and company website/press coverage
  - India startup/business media and public databases
- Keep paid/private connectors pluggable from day one, but not required for v1. The abstraction should allow later adapters for Tracxn, Crunchbase, PitchBook, internal research stores, or proprietary spreadsheets.

---

### Config and Customization

- Expand `config/` beyond the starter YAMLs into:
  - `workflows/{workflow}.yaml` — workflow definitions including checkpoint positions **[CHANGED: checkpoint flags added]**
  - `output_profiles/{profile}.yaml` — output-profile templates
  - `scorecard/weights_base.yaml` — base scorecard weights with normalization rules **[NEW]**
  - `scorecard/weights_{sector}.yaml` — sector overlay weight files **[NEW]**
  - `sources/priority_base.yaml` — source-priority profiles
  - `sources/priority_{sector}.yaml` — sector-specific source priorities
  - `llm.yaml` — single LLM config for all agents **[NEW]**
  - `integrations.yaml` — Linear project/team IDs, webhook URLs **[NEW]**

- Ship a generalist India-first base configuration plus sector overlays for: fintech, SaaS/AI, consumer, healthtech, climate.

- Sector overlays change: relevant sources, diligence questions, scoring weights (must sum to 100), regulatory focus areas.

- Add privacy/source tags to all evidence: `public`, `uploaded_private`, `derived_sensitive`.

- Enforce redaction rules before final synthesis for anything tagged sensitive.

**[NEW] Config validation at startup:**
- Before any workflow runs, a `config_validator` module checks:
  - All referenced agents exist in the agent pool
  - Scorecard weights sum to 100 for base + all sector overlays
  - Output profile templates reference valid section keys
  - Linear API key is present if integration is enabled (warn, not fail)
  - LLM model string is a valid OpenRouter format

---

## Test Plan

- CLI tests for every workflow and output-profile combination.
- Config parsing tests for brief files, overrides, and sector overlays.
- **[NEW]** Config validation tests: weight normalization, missing agent references, invalid model strings.
- Orchestration tests to ensure only workflow-relevant agents run.
- **[NEW]** Checkpoint/resume tests: simulate mid-run failure, verify `run_state.json` correctness, verify resume skips completed agents.
- **[GAP-FIX]** Resume controller tests: verify no-op stub behaviour for completed agents, verify `pending_flags` are correctly re-loaded from `run_state.json`, verify resumed run writes to the original timestamp folder not a new one, verify error message when `--resume` path has no `run_state.json`.
- **[NEW]** `--approve-mode` tests: auto mode runs without pause, manual mode prompts at correct checkpoint positions.
- **[GAP-FIX]** Checkpoint position tests: verify that `checkpoint: true` fires at the exact task positions defined in each workflow YAML, not before or after.
- Evidence-validation tests to ensure every final report section has citations, confidence, and gap flags.
- **[NEW]** Evidence conflict resolution tests: verify tier-based priority, correct `conflict: HIGH/MEDIUM` flagging.
- Source-policy tests for India-first prioritization, source tagging, and private/public handling.
- **[NEW]** Inter-agent context-passing tests: verify `downstream_flags` from one specialist appear in the next agent's task context.
- **[GAP-FIX]** Flag injection tests: verify flags addressed to non-immediate agents are held in `pending_flags` and only injected when that agent is activated; verify no agent receives flags not addressed to it.
- **[NEW]** Renderer tests: verify `ic_memo`, `full_report`, and `one_pager` render correctly from a fixture `findings_bundle.json` without calling any LLM.
- **[GAP-FIX]** `one_pager` self-containment test: parse the rendered HTML and assert zero `<link>`, zero `<script src=...>`, zero `<img src="http...">` tags — all resources must be inline.
- **[NEW]** PDF export tests: verify `weasyprint` produces a valid PDF from both memo and full report markdown.
- **[NEW]** Linear integration tests: mock Linear API, verify correct issue fields are populated from run output.
- **[NEW]** Run versioning tests: verify two runs of same company produce separate timestamped folders and `latest/` symlink updates correctly.
- Golden-path scenario tests for:
  - India fintech DD with brief + deck + financial CSV
  - India SaaS sourcing run from company brief
  - Portfolio review from KPI CSV + notes

---

## Assumptions and Defaults

- v1 interface is CLI + config file, not a web app.
- The 3 top-level workflows are `sourcing`, `due_diligence`, and `portfolio`.
- Output profiles are selectable on every run: `ic_memo`, `full_report`, `one_pager`. **[CHANGED]**
- All 3 output profiles are rendered by deterministic non-LLM renderers from a shared `findings_bundle.json`. **[NEW]**
- OpenRouter is the default LLM path. Single model for all agents in v1. Low temperature (0.2) across all agents. **[CHANGED]**
- Hosted-model usage is allowed for private docs in v1, but source tagging and redaction are mandatory.
- The first implementation optimizes for IC/DD core roles, not the entire VC back office, while leaving extension slots for later expansion.
- Sourcing is always single-company per run. No batch/list mode in v1. **[NEW]**
- Human-in-the-loop checkpoints are toggleable via `--approve-mode {auto|manual}`. Terminal prompt only in v1. Checkpoint positions are pinned in each workflow YAML — not left to runtime inference. **[NEW + GAP-FIX]**
- Resume via `--resume {path}` replays completed agents as no-op stubs and injects prior findings + pending flags as context. The resumed run writes to the original timestamp folder. **[NEW + GAP-FIX]**
- `downstream_flags` are injected into the next relevant agent's task description by the Python controller, not by any LLM. Non-immediate flags are held in `pending_flags` in `run_state.json` until the target agent is activated. **[NEW + GAP-FIX]**
- The `one_pager` HTML output is fully self-contained: all CSS, fonts, JS, and icons are inlined. Zero external dependencies. Safe to email or open offline. **[NEW + GAP-FIX]**
- Run artifacts are versioned by timestamp. Reruns of the same company never overwrite prior runs. **[NEW]**
- Post-run: PDF exported automatically, Linear issue created if API key is configured. No n8n or Notion hooks in v1. **[NEW]**
- The `founder_signal_analyst` uses a defined 8-source fallback hierarchy. LinkedIn scraping is explicitly out of scope. **[NEW]**
- Scorecard ships with generalist India defaults (weights sum to 100). Sector overlays must also sum to 100; enforced by config validator. **[NEW]**
