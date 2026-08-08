"""Third-party-framework `RuntimeAdapter` implementations (LangGraph,
CrewAI, the OpenAI Agents SDK, Semantic Kernel).

Each module here imports its target framework at module level, so it's
only loadable when that framework's package is installed — via the
matching `pyproject.toml` extra (e.g. `pip install "pyagent-blueprint[langgraph]"`).
`AdapterRegistry.discover()` catches the resulting `ImportError` and
skips the adapter rather than failing, exactly like the `pyagent` adapter
does for its own optional `pyagent-patterns`/`pyagent-router`/etc. extra.
"""
