---
name: feature-development-with-tests-and-docs
description: Workflow command scaffold for feature-development-with-tests-and-docs in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-development-with-tests-and-docs

Use this workflow when working on **feature-development-with-tests-and-docs** in `vc-research_crew`.

## Goal

Implements a new feature, adds corresponding tests, and updates documentation.

## Common Files

- `my_agents/src/my_agents/*.py`
- `my_agents/tests/*.py`
- `my_agents/README.md`
- `docs/**/*.mdx`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement or modify feature logic in src/ files.
- Add or update tests in tests/ files.
- Update or add documentation in README.md or docs/.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.