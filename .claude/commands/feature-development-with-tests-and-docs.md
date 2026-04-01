---
name: feature-development-with-tests-and-docs
description: Workflow command scaffold for feature-development-with-tests-and-docs in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-tests-and-docs

Use this workflow when working on **feature-development-with-tests-and-docs** in `vc-research_crew`.

## Goal

Implements a new feature, updates or creates relevant source files, adds or updates tests, and updates documentation if needed.

## Common Files

- `my_agents/src/my_agents/controller.py`
- `my_agents/src/my_agents/llm_policy.py`
- `my_agents/src/my_agents/renderers/*.py`
- `my_agents/src/my_agents/tools/*.py`
- `my_agents/src/my_agents/evals/*.py`
- `my_agents/src/my_agents/schemas.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or create implementation files in src/ (e.g., controller.py, llm_policy.py, renderers, tools, etc.)
- Update or add corresponding test files in tests/ (e.g., test_controller_flow.py, test_renderers.py, test_eval_benchmarks.py, test_quick_mode.py, test_e2e_smoke.py)
- Update documentation or configuration files if needed (e.g., README.md, pyproject.toml, pytest.ini)
- Add or update sample data or config (e.g., sample_briefs/)
- Commit all related changes together

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.