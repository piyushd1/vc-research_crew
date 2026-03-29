import time

from my_agents.evidence import EvidenceRegistry
from my_agents.schemas import AgentFindingResult, FindingRecord, SourcePriorityConfig


def run_benchmark():
    config = SourcePriorityConfig(profile="test_profile", tiers={})
    registry = EvidenceRegistry(source_profile=config)

    # Add a large number of findings to simulate a heavily populated registry
    NUM_AGENTS = 50
    FINDINGS_PER_AGENT = 200

    for i in range(NUM_AGENTS):
        findings = []
        for j in range(FINDINGS_PER_AGENT):
            finding = FindingRecord(
                claim=f"Agent {i} Finding {j}",
                evidence_summary="Test summary",
                source_ref=f"Source {j}",
                source_type="test_source",
                confidence=0.9
            )
            findings.append(finding)

        result = AgentFindingResult(
            agent_name=f"agent_{i}",
            summary=f"Summary for agent {i}",
            findings=findings,
            suggested_section_keys=["section1"]
        )
        registry.add_result(result)


    # Benchmark findings()
    start_time = time.perf_counter()
    ITERATIONS = 1000

    for _ in range(ITERATIONS):
        _ = registry.findings()

    time.perf_counter() - start_time

    # Benchmark summary()
    start_time = time.perf_counter()

    for _ in range(ITERATIONS):
        _ = registry.summary(limit=10)

    time.perf_counter() - start_time

if __name__ == '__main__':
    run_benchmark()
