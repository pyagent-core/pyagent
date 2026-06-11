"""CLI: pyagent-blueprint validate|compile|render|test|diff|generate."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from pyagent_blueprint.loader import BlueprintLoadError, load_blueprint


@click.group()
def cli() -> None:
    """PyAgent Blueprint — declarative agent system specifications."""


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def validate(path: str) -> None:
    """Validate a blueprint YAML/JSON file."""
    from pyagent_blueprint.validator import BlueprintValidator

    try:
        spec = load_blueprint(path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    validator = BlueprintValidator()
    issues = validator.validate(spec)

    if not issues:
        click.echo(f"✓ {path} is valid — no issues found.")
        return

    for issue in issues:
        click.echo(f"[{issue.severity}] {issue.path}: {issue.message}")

    errors = [i for i in issues if i.severity == "error"]
    if errors:
        sys.exit(1)


@cli.command("compile")
@click.argument("path", type=click.Path(exists=True))
def compile_cmd(path: str) -> None:
    """Compile a blueprint and print the runtime graph."""
    from pyagent_blueprint.compiler import BlueprintCompiler, CompilationError

    try:
        spec = load_blueprint(path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    compiler = BlueprintCompiler()
    try:
        graph = compiler.compile(spec)
    except CompilationError as exc:
        click.echo(f"Compilation error: {exc}", err=True)
        sys.exit(1)

    import json

    click.echo(json.dumps(graph.describe(), indent=2))


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-o", "--output", type=click.Path(), default=None, help="Write to file instead of stdout"
)
@click.option("--format", "fmt", type=click.Choice(["mermaid", "markdown"]), default="mermaid")
def render(path: str, output: str | None, fmt: str) -> None:
    """Render a blueprint as a Mermaid diagram or Markdown doc."""
    from pyagent_blueprint.renderer import BlueprintRenderer

    try:
        spec = load_blueprint(path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    renderer = BlueprintRenderer()
    result = renderer.to_markdown(spec) if fmt == "markdown" else renderer.to_mermaid(spec)

    if output:
        Path(output).write_text(result)
        click.echo(f"Written to {output}")
    else:
        click.echo(result)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def test(path: str) -> None:
    """Run contract conformance tests with MockLLM."""
    from pyagent_blueprint.tester import BlueprintTester

    try:
        spec = load_blueprint(path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    tester = BlueprintTester()
    results = asyncio.run(tester.test(spec))
    click.echo(tester.summary(results))

    if any(not r.passed for r in results):
        sys.exit(1)


@cli.command()
@click.argument("old_path", type=click.Path(exists=True))
@click.argument("new_path", type=click.Path(exists=True))
def diff(old_path: str, new_path: str) -> None:
    """Semantic diff between two blueprint versions."""
    from pyagent_blueprint.differ import BlueprintDiffer

    try:
        old_spec = load_blueprint(old_path)
        new_spec = load_blueprint(new_path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    differ = BlueprintDiffer()
    changes = differ.diff(old_spec, new_spec)
    click.echo(differ.summary(changes))


@cli.command()
@click.option("--pattern", required=True, help="Pattern name (e.g., supervisor, pipeline)")
@click.option("--agents", required=True, help="Comma-separated agent names")
@click.option("--name", default="my-blueprint", help="Blueprint name")
@click.option("-o", "--output", type=click.Path(), default=None, help="Write to file")
def generate(pattern: str, agents: str, name: str, output: str | None) -> None:
    """Generate a scaffold blueprint YAML."""
    from pyagent_blueprint.generator import BlueprintGenerator

    generator = BlueprintGenerator()
    try:
        yaml_str = generator.generate(
            pattern=pattern,
            agents=[a.strip() for a in agents.split(",")],
            name=name,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output:
        Path(output).write_text(yaml_str)
        click.echo(f"Written to {output}")
    else:
        click.echo(yaml_str)
