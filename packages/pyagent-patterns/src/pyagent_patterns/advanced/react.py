"""ReAct pattern: Reason → Act → Observe cycle.

The agent iteratively reasons about the task, takes an action (e.g., tool call),
observes the result, then reasons again. Continues until the task is solved
or max steps reached.

LLM calls: 1 per step × max_steps
"""

from __future__ import annotations

from typing import Any, Callable

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


# Tool function type: (action_input: str) -> str
ToolFn = Callable[[str], str]


class ReAct(Pattern):
    """Reasoning + Acting loop with tool use.

    Args:
        agent: The reasoning agent.
        tools: Mapping of tool names to callable functions.
        max_steps: Maximum number of Thought→Action→Observation cycles.
        finish_token: Token in agent response that signals task completion.
    """

    def __init__(
        self,
        agent: Agent,
        tools: dict[str, ToolFn] | None = None,
        max_steps: int = 5,
        finish_token: str = "FINISH",
    ) -> None:
        self._agent = agent
        self._tools = tools or {}
        self._max_steps = max_steps
        self._finish_token = finish_token

    @property
    def pattern_type(self) -> str:
        return "react"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        trace: list[dict[str, Any]] = []

        tool_list = ", ".join(self._tools.keys()) if self._tools else "none"
        system_prompt = (
            f"You are a ReAct agent. Available tools: {tool_list}\n\n"
            f"On each step, respond in this EXACT format:\n"
            f"Thought: [your reasoning]\n"
            f"Action: [tool_name(input)] OR {self._finish_token}[final answer]\n\n"
            f"After receiving an observation, continue reasoning.\n"
            f"When you have the final answer, use: {self._finish_token}[your answer]"
        )

        conversation: list[Message] = [
            Message.system(system_prompt),
            Message.user(ctx.task),
        ]

        for step in range(1, self._max_steps + 1):
            # Agent reasons and decides action
            response = await self._agent.run(conversation)
            messages.append(response)
            conversation.append(response)

            step_data: dict[str, Any] = {"step": step, "response": response.content}

            # Check for finish
            if self._finish_token in response.content:
                # Extract final answer
                parts = response.content.split(self._finish_token, 1)
                final_answer = parts[1].strip() if len(parts) > 1 else response.content
                step_data["action"] = "finish"
                trace.append(step_data)
                break

            # Parse action
            action_name, action_input = self._parse_action(response.content)
            step_data["action"] = action_name
            step_data["action_input"] = action_input

            # Execute tool
            if action_name and action_name in self._tools:
                try:
                    observation = self._tools[action_name](action_input)
                except Exception as e:
                    observation = f"Error: {e}"
                step_data["observation"] = observation
            else:
                observation = f"Unknown tool: {action_name}. Available: {tool_list}"
                step_data["observation"] = observation

            trace.append(step_data)

            # Feed observation back
            obs_msg = Message.user(f"Observation: {observation}")
            conversation.append(obs_msg)
            messages.append(obs_msg)
        else:
            final_answer = messages[-1].content if messages else ""

        return Result(
            output=final_answer,
            messages=messages,
            metadata={
                "steps": len(trace),
                "max_steps": self._max_steps,
                "trace": trace,
                "tools_used": [t["action"] for t in trace if t.get("action") != "finish"],
            },
        )

    @staticmethod
    def _parse_action(content: str) -> tuple[str | None, str]:
        """Parse 'Action: tool_name(input)' from agent response."""
        for line in content.split("\n"):
            line = line.strip()
            if line.lower().startswith("action:"):
                action_text = line.split(":", 1)[1].strip()
                # Parse tool_name(input)
                if "(" in action_text and action_text.endswith(")"):
                    name = action_text[: action_text.index("(")]
                    inp = action_text[action_text.index("(") + 1 : -1]
                    return name.strip(), inp.strip().strip('"').strip("'")
                return action_text, ""
        return None, ""
