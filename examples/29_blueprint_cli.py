"""Example 29: Blueprint CLI usage demo.

Run these commands from the repo root:

    # Validate a blueprint
    pyagent-blueprint validate examples/fixtures/blueprint.yaml

    # Render as Mermaid
    pyagent-blueprint render examples/fixtures/blueprint.yaml

    # Render as Markdown
    pyagent-blueprint render examples/fixtures/blueprint.yaml --format markdown

    # Generate a scaffold
    pyagent-blueprint generate --pattern supervisor --agents "classifier,billing,tech"

    # Semantic diff
    pyagent-blueprint diff v1.yaml v2.yaml

This file demonstrates programmatic CLI invocation:
"""

from click.testing import CliRunner

from pyagent_blueprint.cli import cli


def main() -> None:
    runner = CliRunner()

    # Generate a scaffold
    result = runner.invoke(cli, [
        "generate",
        "--pattern", "pipeline",
        "--agents", "researcher,reviewer",
        "--name", "demo-pipeline",
    ])
    print("=== Generated Blueprint ===")
    print(result.output)

    # Validate from string (save to temp file first)
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(result.output)
        f.flush()

        # Validate
        val_result = runner.invoke(cli, ["validate", f.name])
        print("=== Validation ===")
        print(val_result.output)

        # Render
        render_result = runner.invoke(cli, ["render", f.name])
        print("=== Mermaid ===")
        print(render_result.output)


if __name__ == "__main__":
    main()
