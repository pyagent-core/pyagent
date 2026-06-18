"""CLI entry point: pyagent — Kubernetes-style CLI for agent systems.

Commands:
    pyagent apply <file>             Load and validate a blueprint
    pyagent get agents|workflows|... List resources from a blueprint
    pyagent validate <file>          Run static validation
    pyagent test <file>              Contract conformance tests
    pyagent diff <old> <new>         Semantic diff
    pyagent simulate <file> <wf> <task> [--live]  Run workflow
    pyagent render <file> [--format] Render docs
    pyagent generate --pattern <p> --agents <a,b,c>  Scaffold YAML
    pyagent providers list           List LLM providers
    pyagent providers health         Health check
    pyagent describe <file>          Full blueprint summary
    pyagent dashboard [--port]       Launch web UI
"""

from __future__ import annotations

import asyncio
import sys

import click

from pyagent_studio.services.blueprint_service import BlueprintService
from pyagent_studio.services.governance_service import GovernanceService


@click.group()
def main() -> None:
    """pyagent — Agent System Workbench CLI."""


@main.command()
@click.argument("file", type=click.Path(exists=True))
def apply(file: str) -> None:
    """Load and validate a blueprint YAML file."""
    svc = BlueprintService()
    try:
        spec = svc.load(file)
        issues = svc.validate()
        if issues:
            click.echo(f"Loaded '{spec.metadata.name}' with {len(issues)} issue(s):")
            for issue in issues:
                click.echo(f"  [{issue.severity}] {issue.path}: {issue.message}")
        else:
            click.echo(
                f"✓ Blueprint '{spec.metadata.name}' v{spec.metadata.version} loaded and valid."
            )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("resource", type=click.Choice(["agents", "workflows", "providers", "contracts"]))
@click.argument("file", type=click.Path(exists=True))
def get(resource: str, file: str) -> None:
    """List resources from a loaded blueprint."""
    svc = BlueprintService()
    try:
        spec = svc.load(file)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if resource == "agents":
        for name, agent in spec.agents.items():
            click.echo(f"  {name}  ({agent.description or 'no description'})")
    elif resource == "workflows":
        for name in spec.workflows:
            click.echo(f"  {name}")
    elif resource == "providers":
        for name, prov in spec.providers.items():
            click.echo(f"  {name}  ({prov.model})")
    elif resource == "contracts":
        for name in spec.contracts:
            click.echo(f"  {name}")


@main.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file: str) -> None:
    """Run static validation on a blueprint."""
    svc = BlueprintService()
    try:
        svc.load(file)
        issues = svc.validate()
        if not issues:
            click.echo("Valid")
        else:
            for issue in issues:
                click.echo(f"[{issue.severity}] {issue.path}: {issue.message}")
            sys.exit(1)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command("test")
@click.argument("file", type=click.Path(exists=True))
def test_cmd(file: str) -> None:
    """Run contract conformance tests on a blueprint."""
    svc = BlueprintService()
    try:
        spec = svc.load(file)
        click.echo(f"Testing '{spec.metadata.name}'...")
        issues = svc.validate()
        if not issues:
            click.echo("All contract checks passed.")
        else:
            errors = [i for i in issues if str(i.severity).lower() == "error"]
            warnings = [i for i in issues if str(i.severity).lower() == "warning"]
            click.echo(f"Results: {len(errors)} error(s), {len(warnings)} warning(s)")
            for issue in issues:
                click.echo(f"  [{issue.severity}] {issue.path}: {issue.message}")
            if errors:
                sys.exit(1)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("old_file", type=click.Path(exists=True))
@click.argument("new_file", type=click.Path(exists=True))
def diff(old_file: str, new_file: str) -> None:
    """Compute semantic diff between two blueprints."""
    svc = BlueprintService()
    gov = GovernanceService()
    try:
        old_spec = svc.load(old_file)
        svc2 = BlueprintService()
        new_spec = svc2.load(new_file)
        summary = gov.diff_summary(old_spec, new_spec)
        click.echo(summary if summary else "No differences found.")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.argument("workflow")
@click.argument("task")
@click.option(
    "--live", is_flag=True, default=False, help="Use real LLMs via LiteLLM instead of MockLLM."
)
def simulate(file: str, workflow: str, task: str, live: bool) -> None:
    """Run a workflow simulation (MockLLM by default, --live for real LLMs)."""
    from pyagent_studio.services.simulation_service import SimulationService

    svc = BlueprintService()
    try:
        spec = svc.load(file)
        sim = SimulationService(use_live=live)
        result = asyncio.run(sim.run(spec, workflow, task))

        if result.success:
            click.echo(f"Output: {result.output}")
            click.echo(f"Elapsed: {result.elapsed_ms:.1f}ms")
        else:
            click.echo(f"Error: {result.error}", err=True)
            sys.exit(1)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--format", "fmt", type=click.Choice(["md", "mermaid"]), default="md", help="Output format."
)
def render(file: str, fmt: str) -> None:
    """Render blueprint as Markdown or Mermaid diagram."""
    from pyagent_blueprint import BlueprintRenderer

    svc = BlueprintService()
    try:
        spec = svc.load(file)
        renderer = BlueprintRenderer()
        if fmt == "mermaid":
            click.echo(renderer.to_mermaid(spec))
        else:
            click.echo(renderer.to_markdown(spec))
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--pattern", required=True, help="Pattern type (e.g. pipeline, debate, voting).")
@click.option("--agents", required=True, help="Comma-separated agent names.")
def generate(pattern: str, agents: str) -> None:
    """Scaffold a blueprint YAML from pattern and agents."""
    from pyagent_blueprint import BlueprintGenerator

    try:
        gen = BlueprintGenerator()
        agent_list = [a.strip() for a in agents.split(",")]
        yaml_str = gen.generate(pattern=pattern, agents=agent_list)
        click.echo(yaml_str)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.group()
def providers() -> None:
    """Manage LLM providers."""


@providers.command("list")
def providers_list() -> None:
    """List available LLM models via LiteLLM."""
    try:
        from pyagent_studio.services.provider_service import ProviderService

        svc = ProviderService()
        models = svc.list_models()
        if models:
            for m in models:
                click.echo(f"  {m}")
        else:
            click.echo("No models found.")
    except ImportError:
        click.echo("litellm not installed. Install with: pip install litellm", err=True)
        sys.exit(1)


@providers.command("health")
@click.option("--model", default=None, help="Model to health-check.")
def providers_health(model: str | None) -> None:
    """Run health check on a LLM provider endpoint."""
    try:
        from pyagent_studio.services.provider_service import ProviderService

        svc = ProviderService()
        result = asyncio.run(svc.health_check(model))
        if result["healthy"]:
            click.echo(f"✓ {result['model']} is healthy")
        else:
            click.echo(f"✗ {result['model']}: {result.get('error', 'unknown')}", err=True)
            sys.exit(1)
    except ImportError:
        click.echo("litellm not installed. Install with: pip install litellm", err=True)
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
def describe(file: str) -> None:
    """Print full blueprint summary."""
    svc = BlueprintService()
    try:
        svc.load(file)
        info = svc.summary()
        for key, value in info.items():
            click.echo(f"  {key}: {value}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.option("--port", default=8420, type=int, help="Web dashboard port.")
@click.option("--host", default="127.0.0.1", help="Web dashboard host.")
@click.option(
    "--trace",
    "trace_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a recorded trace JSONL file to load on the Overview dashboard.",
)
@click.option(
    "--blueprint",
    "blueprint_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a blueprint YAML to load for the resource tabs (defaults to a bundled sample).",
)
def dashboard(port: int, host: str, trace_path: str | None, blueprint_path: str | None) -> None:
    """Launch the web dashboard."""
    try:
        import uvicorn
    except ImportError:
        click.echo(
            "uvicorn not installed. Install with: pip install pyagent-studio[web]",
            err=True,
        )
        sys.exit(1)

    from pyagent_studio.web.app import create_app

    click.echo(f"Starting dashboard at http://{host}:{port}")
    if trace_path:
        click.echo(f"Loading trace: {trace_path}")
    if blueprint_path:
        click.echo(f"Loading blueprint: {blueprint_path}")
    app = create_app(trace_path=trace_path, blueprint_path=blueprint_path)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
