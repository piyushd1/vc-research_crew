from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from my_agents.configuration import load_app_config
from my_agents.llm_policy import validate_llm_config
from my_agents.renderers import render_full_report, render_ic_memo, render_one_pager
from my_agents.schemas import (
    FindingsBundle,
    LLMConfig,
    OutputProfile,
    ScorecardDimension,
    ScorecardSummary,
    WorkflowType,
)


class ConfigAndRendererTests(unittest.TestCase):
    def test_llm_policy_rejects_closed_models_when_oss_only(self) -> None:
        config = LLMConfig(
            provider="openrouter",
            model="openrouter/openai/gpt-4o",
            api_key_env="OPENROUTER_API_KEY",
            open_source_only=True,
            allow_closed_models=False,
        )
        with self.assertRaises(ValueError):
            validate_llm_config(config)

    def test_app_config_loads_and_sector_weights_sum_to_100(self) -> None:
        config = load_app_config(PROJECT_ROOT / "src" / "my_agents" / "config")
        weights = config.resolve_score_weights("fintech")
        self.assertEqual(sum(weights.values()), 100)

    def test_renderers_create_expected_outputs(self) -> None:
        bundle = FindingsBundle(
            company_name="Acme Ventures",
            workflow=WorkflowType.DUE_DILIGENCE,
            summary="Acme is a promising India fintech company.",
            sections={
                "executive_summary": "Acme has strong early traction.",
                "company_snapshot": "Acme builds payments infrastructure.",
                "investment_recommendation": "Conditional investment with two open diligence items.",
                "next_steps": "Validate lending partner risk.",
            },
            scorecard=ScorecardSummary(
                overall_score=78.0,
                recommendation="STRONG INTEREST",
                dimensions=[
                    ScorecardDimension(
                        dimension="market_size_and_growth",
                        weight=20,
                        score=4,
                        rationale="Large India TAM.",
                    )
                ],
            ),
            top_signals=["Large market", "Strong founder signal"],
            top_risks=["Regulatory dependency"],
            open_questions=["What is the true CAC payback?"],
            evidence_gaps=["Need audited FY25 financials"],
            citations=["https://example.com/source"],
        )
        memo = render_ic_memo(bundle)
        report = render_full_report(bundle)
        one_pager = render_one_pager(bundle)

        self.assertIn("# IC Memo: Acme Ventures", memo)
        self.assertIn("# Full Report: Acme Ventures", report)
        self.assertIn("Acme Ventures One Pager", one_pager)
        self.assertNotIn("<link", one_pager.lower())
        self.assertNotIn("script src=", one_pager.lower())
        self.assertNotIn('img src="http', one_pager.lower())


if __name__ == "__main__":
    unittest.main()
