"""Example: Talker-Reasoner — fast cheap model + slow expensive model."""

import asyncio

from pyagent_patterns.advanced import TalkerReasoner
from pyagent_patterns.base import Agent, MockLLM


async def main():
    pattern = TalkerReasoner(
        talker=Agent("talker", MockLLM(responses=["The capital of France is Paris."])),
        reasoner=Agent("reasoner", MockLLM(responses=["Deep analysis of quantum effects..."])),
    )

    # Easy question → talker handles it
    result = await pattern.run("What is the capital of France?")
    print(f"Easy Q: {result.output}")
    print(f"System: {result.metadata['system']}, Escalated: {result.metadata['escalated']}")

    # Hard question → talker says "I'm not sure", escalates to reasoner
    pattern2 = TalkerReasoner(
        talker=Agent("talker", MockLLM(responses=["I'm not sure about quantum field theory..."])),
        reasoner=Agent("reasoner", MockLLM(responses=["Quantum field theory unifies QM and SR..."])),
    )
    result2 = await pattern2.run("Explain quantum field theory")
    print(f"\nHard Q: {result2.output}")
    print(f"System: {result2.metadata['system']}")

if __name__ == "__main__":
    asyncio.run(main())
