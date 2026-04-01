---
name: ecc-bundle-addition
description: Workflow command scaffold for ecc-bundle-addition in vc-research_crew.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /ecc-bundle-addition

Use this workflow when working on **ecc-bundle-addition** in `vc-research_crew`.

## Goal

Adds or updates an ECC bundle for a new skill/agent, including command docs, identity, skills, and agent configs.

## Common Files

- `.claude/commands/*.md`
- `.claude/identity.json`
- `.claude/ecc-tools.json`
- `.claude/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/SKILL.md`
- `.agents/skills/vc-research_crew/agents/openai.yaml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add or update .claude/commands/*.md (such as feature-development.md, refactoring.md, feature-development-with-tests-and-docs.md, ecc-bundle-addition.md)
- Add or update .claude/identity.json
- Add or update .claude/ecc-tools.json
- Add or update .claude/skills/vc-research_crew/SKILL.md
- Add or update .agents/skills/vc-research_crew/SKILL.md

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.