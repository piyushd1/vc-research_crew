import time
import unittest

from my_agents.evidence import EvidenceRegistry
from my_agents.schemas import AgentFindingResult, FindingRecord, SourcePriorityConfig


class TestEvidenceRegistry(unittest.TestCase):
    def test_performance_findings(self):
        # Setup test data
        registry = EvidenceRegistry(source_profile=SourcePriorityConfig(profile="test", tiers={}))
        for i in range(100):
            findings = [FindingRecord(claim=f"Claim {i}-{j}", evidence_summary="test summary", source_ref="test_source", source_type="test", confidence=0.9) for j in range(100)]
            registry.add_result(AgentFindingResult(agent_name=f"agent_{i}", summary="test", findings=findings))

        # Benchmark original/current behavior
        start = time.perf_counter()
        for _ in range(1000):
            _ = registry.findings()
        end = time.perf_counter()

        # We expect it to be very fast due to caching (should be ~0.00x seconds)
        duration = end - start
        self.assertLess(duration, 0.05, f"Time taken {duration:.4f} is not fast enough, expected <0.05 seconds with caching")
