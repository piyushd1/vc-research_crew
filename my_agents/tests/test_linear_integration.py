from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from my_agents.integrations.linear_push import build_linear_issue_payload, push_linear_issue
from my_agents.schemas import (
    FindingsBundle,
    IntegrationsConfig,
    OutputProfile,
    ScorecardSummary,
    WorkflowType,
)


class LinearIntegrationTests(unittest.TestCase):
    def _bundle(self) -> FindingsBundle:
        return FindingsBundle(
            company_name="Acme Ventures",
            workflow=WorkflowType.SOURCING,
            summary="Summary",
            sections={"executive_summary": "Summary"},
            scorecard=ScorecardSummary(overall_score=66.0, recommendation="CONDITIONAL"),
            top_signals=["Signal 1"],
            top_risks=["Risk 1"],
        )

    def test_payload_contains_run_context(self) -> None:
        payload = build_linear_issue_payload(
            self._bundle(),
            WorkflowType.SOURCING,
            OutputProfile.ONE_PAGER,
            Path("/tmp/run-folder"),
        )
        self.assertIn("Acme Ventures - sourcing", payload["title"])
        self.assertIn("Run folder: /tmp/run-folder", payload["description"])

    def test_push_is_non_blocking_without_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            pushed = push_linear_issue(
                bundle=self._bundle(),
                workflow=WorkflowType.SOURCING,
                output_profile=OutputProfile.ONE_PAGER,
                run_dir=Path("/tmp/run-folder"),
                integrations=IntegrationsConfig.model_validate(
                    {"linear": {"enabled": True, "team_id": "VC", "project_id": "VC"}}
                ),
            )
        self.assertFalse(pushed)


if __name__ == "__main__":
    unittest.main()
