from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from my_agents.controller import VCResearchController
from my_agents.schemas import (
    AgentFindingResult,
    ApproveMode,
    AuditResult,
    FindingRecord,
    FindingsBundle,
    OutputProfile,
    RunRequest,
    ScorecardSummary,
    WorkflowType,
)


class FakeRunner:
    def run_agent(
        self,
        agent_name: str,
        spec,
        prompt: str,
        response_model,
        llm,
        tools,
        verbose: bool = False,
    ):
        if response_model is AgentFindingResult:
            return AgentFindingResult(
                agent_name=agent_name,
                summary=f"{agent_name} completed review",
                findings=[
                    FindingRecord(
                        claim=f"{agent_name} identified a useful signal",
                        evidence_summary="Grounded in the brief and deterministic test fixture.",
                        source_ref="brief://company",
                        source_type="uploaded_private",
                        confidence=0.8,
                    )
                ],
                suggested_section_keys=["company_snapshot", "top_signals"],
            )
        if response_model is AuditResult:
            return AuditResult(passed=True, issues=[], gaps=[])
        if response_model is FindingsBundle:
            return FindingsBundle(
                company_name="Test D2C Brand",
                workflow=WorkflowType.SOURCING,
                summary="Synthesized summary",
                sections={
                    "executive_summary": "Summary",
                    "company_snapshot": "Snapshot",
                    "top_signals": "Signals",
                    "top_risks": "Risks",
                    "open_questions": "Questions",
                    "next_steps": "Next steps",
                },
                scorecard=ScorecardSummary(overall_score=75.0, recommendation="Investigate"),
                top_signals=["Strong category pull"],
                top_risks=["Channel concentration"],
                citations=["brief://company"],
            )
        raise AssertionError(f"Unexpected response model: {response_model}")


class ControllerFlowTests(unittest.TestCase):
    def test_sourcing_run_completes_for_d2c_alias_sector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            docs_dir = project_root / "docs"
            docs_dir.mkdir()
            (docs_dir / "metrics.csv").write_text(
                "month,revenue\nJan,100\nFeb,140\n",
                encoding="utf-8",
            )
            brief_path = project_root / "brief.yaml"
            brief_path.write_text(
                "\n".join(
                    [
                        "company_name: Test D2C Brand",
                        "website: https://example.com",
                        "sector: d2c brands",
                        "stage: series_a",
                        "geography: India",
                        "one_line: Omnichannel clean-label snack brand.",
                        f"docs_dir: {docs_dir}",
                    ]
                ),
                encoding="utf-8",
            )

            controller = VCResearchController(
                runner=FakeRunner(),
                project_root=project_root,
            )
            request = RunRequest(
                workflow=WorkflowType.SOURCING,
                brief_path=brief_path,
                output_profile=OutputProfile.ONE_PAGER,
                approve_mode=ApproveMode.AUTO,
            )

            with patch("my_agents.controller.build_llm", return_value=object()):
                artifacts = controller.run(request)

            self.assertTrue(artifacts.report_path.exists())
            self.assertTrue(artifacts.one_pager_path is not None)
            self.assertTrue(artifacts.one_pager_path.exists())
            self.assertTrue(artifacts.sources_path.exists())
            state = json.loads(artifacts.run_state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["workflow"], "sourcing")
            self.assertEqual(len(state["completed_agents"]), 4)


if __name__ == "__main__":
    unittest.main()
