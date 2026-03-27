from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from my_agents.controller import VCResearchController
from my_agents.schemas import (
    AgentFindingResult,
    ApprovalAction,
    AuditResult,
    DimensionScore,
    DownstreamFlag,
    FindingRecord,
    OutputProfile,
    RunRequest,
    WorkflowType,
)


class FakeRunner:
    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls: list[str] = []
        self.prompts: dict[str, str] = {}

    def run_agent(
        self,
        agent_name,
        spec,
        prompt,
        response_model,
        llm,
        tools,
        verbose=False,
    ):
        self.calls.append(agent_name)
        self.prompts[agent_name] = prompt
        if self.fail_on == agent_name:
            raise RuntimeError(f"simulated failure for {agent_name}")

        if response_model is AuditResult:
            return AuditResult(passed=True)

        if response_model.__name__ == "FindingsBundle":
            raise RuntimeError("force deterministic fallback bundle")

        dimension = None
        if agent_name == "startup_sourcer":
            dimension = DimensionScore(
                dimension="market_size_and_growth",
                score=4,
                rationale="Large market.",
            )
        elif agent_name == "thesis_fit_analyst":
            dimension = DimensionScore(
                dimension="founder_quality_and_signal",
                score=4,
                rationale="Good fit.",
            )
        elif agent_name == "market_mapper":
            dimension = DimensionScore(
                dimension="gtm_traction_and_momentum",
                score=3,
                rationale="Moderate traction.",
            )
        elif agent_name == "founder_signal_analyst":
            dimension = DimensionScore(
                dimension="founder_quality_and_signal",
                score=5,
                rationale="Strong founder signal.",
            )

        flags = []
        if agent_name == "thesis_fit_analyst":
            flags = [
                DownstreamFlag(
                    flag="watch_regulation",
                    for_agent="market_mapper",
                    detail="Evaluate regulatory barriers in India.",
                )
            ]

        return AgentFindingResult(
            agent_name=agent_name,
            summary=f"Summary for {agent_name}",
            findings=[
                FindingRecord(
                    claim=f"Claim from {agent_name}",
                    evidence_summary=f"Evidence from {agent_name}",
                    source_ref=f"https://example.com/{agent_name}",
                    source_type="public_web",
                    confidence=0.8,
                    claim_key=f"{agent_name}_claim",
                    claim_value=agent_name,
                )
            ],
            dimension_scores=[dimension] if dimension else [],
            open_questions=[f"Open question from {agent_name}"],
            downstream_flags=flags,
        )


class ControllerTests(unittest.TestCase):
    def _write_brief(self, root: Path) -> Path:
        brief_path = root / "brief.json"
        brief_path.write_text(
            json.dumps(
                {
                    "company_name": "Acme Ventures",
                    "website": "https://acme.example",
                    "sector": "fintech",
                    "stage": "seed",
                    "geography": "India",
                    "one_line": "Infrastructure for payments.",
                }
            ),
            encoding="utf-8",
        )
        return brief_path

    def test_controller_creates_run_artifacts_and_checkpoint_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            brief_path = self._write_brief(tmp_root)
            runner = FakeRunner()
            controller = VCResearchController(
                runner=runner,
                project_root=tmp_root,
                prompt_fn=lambda _: "approve",
                now_fn=lambda: datetime(2026, 1, 2, 3, 4, 5),
            )
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=False):
                artifacts = controller.run(
                    RunRequest(
                        workflow=WorkflowType.SOURCING,
                        brief_path=brief_path,
                        output_profile=OutputProfile.ONE_PAGER,
                    )
                )

            self.assertTrue(artifacts.run_dir.exists())
            self.assertTrue((artifacts.run_dir / "run_state.json").exists())
            self.assertTrue((artifacts.run_dir / "scorecard.json").exists())
            self.assertTrue((artifacts.run_dir / "one_pager.html").exists())
            self.assertTrue((artifacts.run_dir.parent / "latest").is_symlink())
            state = json.loads((artifacts.run_dir / "run_state.json").read_text("utf-8"))
            self.assertIn("thesis_fit_analyst", state["checkpoint_history"])
            self.assertIn("watch_regulation", runner.prompts["market_mapper"])

    def test_resume_reuses_original_run_folder_and_skips_completed_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            brief_path = self._write_brief(tmp_root)
            crash_runner = FakeRunner(fail_on="market_mapper")
            controller = VCResearchController(
                runner=crash_runner,
                project_root=tmp_root,
                now_fn=lambda: datetime(2026, 1, 2, 3, 4, 5),
            )
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=False):
                with self.assertRaises(RuntimeError):
                    controller.run(
                        RunRequest(
                            workflow=WorkflowType.SOURCING,
                            brief_path=brief_path,
                            output_profile=OutputProfile.ONE_PAGER,
                        )
                    )

            run_dir = tmp_root / "runs" / "acme-ventures" / "2026-01-02_030405"
            self.assertTrue(run_dir.exists())
            resumed_runner = FakeRunner()
            resumed_controller = VCResearchController(
                runner=resumed_runner,
                project_root=tmp_root,
                now_fn=lambda: datetime(2026, 1, 2, 3, 4, 5),
            )
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=False):
                artifacts = resumed_controller.run(
                    RunRequest(
                        resume=run_dir,
                        output_profile=OutputProfile.ONE_PAGER,
                    )
                )

            self.assertEqual(artifacts.run_dir.resolve(), run_dir.resolve())
            self.assertNotIn("startup_sourcer", resumed_runner.calls)
            self.assertIn("market_mapper", resumed_runner.calls)

    def test_manual_checkpoint_can_abort(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            brief_path = self._write_brief(tmp_root)
            controller = VCResearchController(
                runner=FakeRunner(),
                project_root=tmp_root,
                prompt_fn=lambda _: "abort",
                now_fn=lambda: datetime(2026, 1, 2, 3, 4, 5),
            )
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=False):
                with self.assertRaises(SystemExit):
                    controller.run(
                        RunRequest(
                            workflow=WorkflowType.SOURCING,
                            brief_path=brief_path,
                            output_profile=OutputProfile.ONE_PAGER,
                            approve_mode="manual",
                        )
                    )


if __name__ == "__main__":
    unittest.main()
