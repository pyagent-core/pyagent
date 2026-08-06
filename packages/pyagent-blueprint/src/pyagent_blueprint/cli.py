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


@cli.command("package")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(),
    default="dist",
    help="Output directory for the packaged Agent Unit (default: dist)",
)
def package_cmd(path: str, output_dir: str) -> None:
    """Package a blueprint into a distributable 'Agent Unit' archive.

    Requires the blueprint to declare a top-level 'package:' block with at
    least 'name' and 'runtime'.
    """
    from pyagent_blueprint.packaging import PackagingError, package_blueprint

    try:
        spec = load_blueprint(path)
    except BlueprintLoadError as exc:
        click.echo(f"Load error: {exc}", err=True)
        sys.exit(1)

    raw_source = Path(path).read_text(encoding="utf-8")

    try:
        archive_path = package_blueprint(spec, raw_source, path, output_dir)
    except PackagingError as exc:
        click.echo(f"Packaging error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"✓ Packaged Agent Unit written to {archive_path}")


@cli.command("adapters")
def adapters_cmd() -> None:
    """List discoverable RuntimeAdapters and their capabilities."""
    from pyagent_blueprint.adapter import AdapterRegistry

    discovered = AdapterRegistry.discover()
    if not discovered:
        click.echo(
            "No adapters discovered. Install an adapter package "
            "(e.g. 'pip install pyagent-blueprint[pyagent]') to enable one."
        )
        return

    for adapter_name, adapter_cls in sorted(discovered.items()):
        caps = getattr(adapter_cls, "capabilities", None)
        click.echo(f"{adapter_name}: {caps}")


@cli.command("adapter-template")
@click.option("--framework", required=True, help="Human-readable SDK name, e.g. 'LangGraph'")
@click.option(
    "--adapter-name", default=None, help="entry-point/RuntimeAdapter.name (default: derived)"
)
@click.option("--dist-name", default=None, help="PyPI distribution name (default: derived)")
@click.option(
    "-o", "--output", "output_dir", type=click.Path(), required=True, help="Output directory"
)
def adapter_template_cmd(
    framework: str, adapter_name: str | None, dist_name: str | None, output_dir: str
) -> None:
    """Scaffold a starter RuntimeAdapter package for a third-party SDK.

    Generates a pyproject.toml with the entry point pre-wired, a stub
    adapter module, a conformance test file, and a README.
    """
    from pyagent_blueprint.adapter_template import write_adapter_template

    out_dir = write_adapter_template(
        framework_name=framework,
        output_dir=output_dir,
        adapter_name=adapter_name,
        dist_name=dist_name,
    )
    click.echo(f"✓ Adapter template for '{framework}' scaffolded at {out_dir}")
