"""Hierarchical Coordination pattern: Manager → Teams → Workers.

A tiered approach where a manager delegates to team leads,
who further delegate to individual workers. Results flow back
up through the hierarchy.

LLM calls: 1 manager + T team leads + W workers
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


@dataclass
class Team:
    """A team with a lead agent and worker agents.

    Args:
        name: Team name (e.g., "Research", "Risk").
        lead: The team lead agent who coordinates workers.
        workers: Individual worker agents on this team.
    """

    name: str
    lead: Agent
    workers: list[Agent]


class Hierarchical(Pattern):
    """Manager → Team Leads → Workers hierarchical coordination.

    Args:
        manager: Top-level manager that decomposes work and synthesizes results.
        teams: List of teams, each with a lead and workers.
    """

    def __init__(self, manager: Agent, teams: list[Team]) -> None:
        self._manager = manager
        self._teams = teams

    @property
    def pattern_type(self) -> str:
        return "hierarchical"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        # Step 1: Manager decomposes task
        decompose_prompt = Message.user(
            f"Decompose this task into subtasks for these teams: "
            f"{', '.join(t.name for t in self._teams)}.\n"
            f"For each team, provide a clear subtask description.\n\n"
            f"Task: {ctx.task}"
        )
        manager_plan = await self._manager.run([decompose_prompt])
        messages.append(manager_plan)

        # Step 2: Teams work in parallel
        async def _run_team(team: Team, plan: str) -> tuple[str, list[Message]]:
            team_msgs: list[Message] = []

            # Team lead delegates to workers
            worker_tasks = [
                worker.run([Message.user(f"Team {team.name} task: {plan}\nDo your part.")])
                for worker in team.workers
            ]
            worker_results = await asyncio.gather(*worker_tasks)
            team_msgs.extend(worker_results)

            # Team lead synthesizes worker outputs
            worker_summary = "\n".join(
                f"- {team.workers[i].name}: {r.content}" for i, r in enumerate(worker_results)
            )
            lead_msg = Message.user(
                f"Synthesize your team's work:\n{worker_summary}"
            )
            lead_result = await team.lead.run([lead_msg])
            team_msgs.append(lead_result)
            return lead_result.content, team_msgs

        team_tasks = [_run_team(team, manager_plan.content) for team in self._teams]
        team_outputs = await asyncio.gather(*team_tasks)

        for _, team_msgs in team_outputs:
            messages.extend(team_msgs)

        # Step 3: Manager synthesizes all team outputs
        team_summary = "\n\n".join(
            f"--- {self._teams[i].name} Team ---\n{output}"
            for i, (output, _) in enumerate(team_outputs)
        )
        synthesis_prompt = Message.user(
            f"Synthesize these team outputs into a final response:\n\n{team_summary}"
        )
        final = await self._manager.run([synthesis_prompt])
        messages.append(final)

        return Result(
            output=final.content,
            messages=messages,
            metadata={
                "teams": len(self._teams),
                "total_workers": sum(len(t.workers) for t in self._teams),
                "team_names": [t.name for t in self._teams],
            },
        )
