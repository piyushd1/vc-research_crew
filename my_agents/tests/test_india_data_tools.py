from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from my_agents.tools.india_data_tools import (
    CrunchbaseCompanyTool,
    GooglePlayStoreTool,
    IndiaJobSignalTool,
    ToflerCompanyTool,
    TracxnCompanyTool,
)


class IndiaDataToolImportTests(unittest.TestCase):
    """Verify all five tools are importable and are BaseTool instances."""

    def test_all_tools_importable(self) -> None:
        from crewai.tools import BaseTool

        tools = [
            ToflerCompanyTool(),
            TracxnCompanyTool(),
            CrunchbaseCompanyTool(),
            GooglePlayStoreTool(),
            IndiaJobSignalTool(),
        ]
        for tool in tools:
            self.assertIsInstance(tool, BaseTool)


class IndiaDataToolNameTests(unittest.TestCase):
    """Each tool must have the correct .name attribute."""

    def test_tofler_name(self) -> None:
        self.assertEqual(ToflerCompanyTool().name, "tofler_company_lookup")

    def test_tracxn_name(self) -> None:
        self.assertEqual(TracxnCompanyTool().name, "tracxn_company_lookup")

    def test_crunchbase_name(self) -> None:
        self.assertEqual(CrunchbaseCompanyTool().name, "crunchbase_company_lookup")

    def test_google_play_name(self) -> None:
        self.assertEqual(GooglePlayStoreTool().name, "google_play_store_lookup")

    def test_india_job_signal_name(self) -> None:
        self.assertEqual(IndiaJobSignalTool().name, "india_job_signal")


class IndiaDataToolMissingKeyTests(unittest.TestCase):
    """All tools must return a clear message when TAVILY_API_KEY is absent."""

    def _env_without_tavily(self) -> dict[str, str]:
        env = os.environ.copy()
        env.pop("TAVILY_API_KEY", None)
        return env

    def test_tofler_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            result = ToflerCompanyTool()._run(company_name="Razorpay")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_tracxn_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            result = TracxnCompanyTool()._run(company_name="Razorpay")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_crunchbase_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            result = CrunchbaseCompanyTool()._run(company_name="Razorpay")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_google_play_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            result = GooglePlayStoreTool()._run(company_name="Razorpay")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_india_job_signal_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            result = IndiaJobSignalTool()._run(company_name="Razorpay")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")


if __name__ == "__main__":
    unittest.main()
