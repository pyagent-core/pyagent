"""Orchestrator-Workers pattern: central LLM dynamically delegates tasks to workers.

Unlike Supervisor (static routes) or Hierarchical (fixed teams), the Orchestrator
dynamically decides how many workers to spawn and what each should do.

LLM calls: 1 planning + N workers (dynamic) + 1 synthesis
"""

from __future__ import annotations

import asyncio
import json

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class OrchestratorWorkers(Pattern):
    """Dynamic task delegation: orchestrator plans → workers execute → synthesize.

    Args:
        orchestrator: Agent that plans the work and synthesizes results.
        workers: Pool of available worker agents. The orchestrator selects from these.
    """

    def __init__(self, orchestrator: Agent, workers: list[Agent]) -> None:
        self._orchestrator = orchestrator
        self._workers = {w.name: w for w in workers}

    @property
    def pattern_type(self) -> str:
        return "orchestrator_workers"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        worker_names = list(self._workers.keys())

        # Step 1: Orchestrator plans the work
        plan_prompt = Message.user(
            f"You have these workers available: {', '.join(worker_names)}.\n"
            f"Plan how to accomplish this task by assigning subtasks to workers.\n"
            f'Respond as JSON: {{"assignments": [{{"worker": "name", "subtask": "description"}}]}}\n\n'
            f"Task: {ctx.task}"
        )
        plan_msg = await self._orchestrator.run([plan_prompt])
        messages.append(plan_msg)

        # Step 2: Parse assignments and dispatch
        assignments = self._parse_assignments(plan_msg.content)
        worker_results: list[tuple[str, str]] = []

        async def _run_assignment(worker_name: str, subtask: str) -> tuple[str, str]:
            worker = self._workers.get(worker_name)
            if worker is None:
                # Fallback to first available worker
                worker = next(iter(self._workers.values()))
            result = await worker.run([Message.user(subtask)])
            return worker.name, result.content

        tasks = [_run_assignment(a["worker"], a["subtask"]) for a in assignments]
        results = await asyncio.gather(*tasks)
        for name, content in results:
            messages.append(Message.assistant(content, name=name))
            worker_results.append((name, content))

        # Step 3: Orchestrator synthesizes
        results_summary = "\n\n".join(
            f"--- {name} ---\n{content}" for name, content in worker_results
        )
        synthesis_prompt = Message.user(
            f"Synthesize these worker results into a final response:\n\n{results_summary}"
        )
        final = await self._orchestrator.run([synthesis_prompt])
        messages.append(final)

        return Result(
            output=final.content,
            messages=messages,
            metadata={
                "assignments": assignments,
                "workers_used": len(assignments),
            },
        )

    @staticmethod
    def _parse_assignments(content: str) -> list[dict[str, str]]:
        """Parse orchestrator's JSON assignment plan. Falls back gracefully."""
        try:
            # Try to extract JSON from the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
                return data.get("assignments", [])
        except (json.JSONDecodeError, KeyError):
            pass
        # Fallback: single assignment to first worker
        return [{"worker": "default", "subtask": content}]
