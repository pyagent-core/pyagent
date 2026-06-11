"""Example 25: Full-stack hook-based integration.

Blueprint → Compile → Wire hooks → Run → Observe.

Demonstrates:
- Blueprint YAML → RuntimeGraph compilation
- Hook-based wiring of trace, context, compression, cost tracking
- TraceEventBus with ConsoleExporter
- ContextLedger reading/writing per agent
- Compression on agent output
- End-to-end cost tracking
"""

import asyncio

from pyagent_blueprint import load_blueprint_from_str, BlueprintCompiler
from pyagent_compress import MessageCompressor
from pyagent_context import ContextLedger
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter

BLUEPRINT_YAML = """\
api_version: pyagent/v1
metadata:
  name: customer-support
  version: 1.0.0

providers:
  primary:
    model: gpt-4o-mini

agents:
  classifier:
    prompt: "Classify the user request into one of: billing, tech, general. Reply with just the category."
    provider: primary
  billing:
    prompt: "You are a billing specialist. Handle billing inquiries professionally."
    provider: primary
  tech:
    prompt: "You are a tech support specialist. Help users with technical issues."
    provider: primary

workflows:
  support:
    pattern: supervisor
    agents:
      classifier: classifier
      routes:
        billing: billing
        tech: tech

observability:
  tracing:
    enabled: true
  cost_budget:
    daily_usd: 50.0
    alert_threshold: 0.8

context:
  compression:
    policy: semantic_lossless
    target_ratio: 0.6
"""


async def main():
    # 1. Load & compile blueprint
    spec = load_blueprint_from_str(BLUEPRINT_YAML)
    graph = BlueprintCompiler().compile(spec)
    print(f"1. Compiled blueprint: {graph.workflow_names}")
    print(f"   Agents: {list(graph.agents.keys())}")

    # 2. Wire hooks
    bus = TraceEventBus()
    ledger = ContextLedger()
    compressor = MessageCompressor(target_ratio=0.5)
    tracker = CostTracker(event_bus=bus)

    graph.wire_trace(bus)
    graph.wire_context(ledger)
    graph.wire_compressor(compressor)
    graph.wire_cost_tracker(tracker)
    print("2. Hooks wired: trace, context, compressor, cost_tracker")

    # 3. Subscribe console exporter to trace bus
    console = ConsoleExporter()
    bus.subscribe(console.export_event)
    print("3. ConsoleExporter subscribed to TraceEventBus\n")

    # 4. Run the workflow
    print("--- Running workflow 'support' ---")
    result = await graph.run("support", "I can't see my invoice for last month")
    print(f"\n4. Result: {result.output[:120]}...")
    print(f"   Duration: {result.duration_seconds:.3f}s")
    print(f"   Tokens: ~{result.token_estimate}")

    # 5. Inspect context ledger
    print(f"\n5. Context ledger: {len(ledger)} items, ~{ledger.total_tokens} tokens")
    for item in ledger.items:
        print(f"   [{item.source}] {item.content[:80]}...")

    # 6. Cost summary
    print(f"\n6. Cost: ${tracker.total_cost:.6f}")
    print(f"   By agent: {tracker.by_agent()}")
    print(f"   Total tokens: {tracker.total_tokens}")


if __name__ == "__main__":
    asyncio.run(main())
