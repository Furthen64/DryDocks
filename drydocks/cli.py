"""
Click CLI for DryDocks test suite.
"""

import click
import sys
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .api import LLMClient
from .runner import TestRunner
from .reporting import ReportFormatter


@click.group()
def cli():
    """DryDocks: Professional LLM API test suite."""
    pass


@cli.command()
def setup():
    """Interactive setup wizard to configure DryDocks."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("DryDocks Setup")
    click.echo("=" * 60)
    click.echo("")

    config = ConfigManager()

    # Prompt for settings
    endpoint = click.prompt(
        "LLM API endpoint",
        default=config.get("endpoint", "http://127.0.0.1:8080/v1/messages"),
    )
    api_key = click.prompt(
        "API key",
        default=config.get("api_key", "dummy"),
        hide_input=False,
    )
    model = click.prompt(
        "Model name",
        default=config.get("model", "qwen"),
    )
    timeout = click.prompt(
        "Timeout (seconds)",
        default=config.get("timeout_seconds", 120),
        type=int,
    )
    max_retries = click.prompt(
        "Max retries",
        default=config.get("max_retries", 2),
        type=int,
    )
    retry_delay = click.prompt(
        "Retry delay (seconds)",
        default=config.get("retry_delay_seconds", 1),
        type=float,
    )

    # Update config
    config.set("endpoint", endpoint)
    config.set("api_key", api_key)
    config.set("model", model)
    config.set("timeout_seconds", timeout)
    config.set("max_retries", max_retries)
    config.set("retry_delay_seconds", retry_delay)

    click.echo("")
    click.echo("Testing connection...")

    valid, message = config.validate()
    if valid:
        click.secho(f"✓ {message}", fg="green")
        config.save()
        click.echo(f"✓ Config saved to {ConfigManager.CONFIG_FILE}")
    else:
        click.secho(f"✗ {message}", fg="red")
        click.echo("Setup cancelled.")
        sys.exit(1)

    click.echo("")


@cli.command()
def status():
    """Check DryDocks configuration and connection status."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("DryDocks Status")
    click.echo("=" * 60)
    click.echo("")

    config = ConfigManager()

    if not config.exists():
        click.secho("✗ No configuration found", fg="red")
        click.echo(f"Run 'drydocks setup' to initialize: {ConfigManager.CONFIG_FILE}")
        sys.exit(1)

    click.echo("Configuration:")
    for key, value in config.to_display_dict().items():
        click.echo(f"  {key}: {value}")

    click.echo("")
    click.echo("Testing connection...")
    valid, message = config.validate()

    if valid:
        click.secho(f"✓ {message}", fg="green")
    else:
        click.secho(f"✗ {message}", fg="red")
        sys.exit(1)

    click.echo("")


@cli.command()
@click.argument("test_name", default="all")
@click.option(
    "--runs",
    default=5,
    type=int,
    help="Number of iterations per test",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print detailed output",
)
def run(test_name: str, runs: int, verbose: bool):
    """
    Run tests.

    TEST_NAME: Test to run ('all', 'pong', 'json', 'tool_use', 'agent_flow')
    """
    config = ConfigManager()

    # Check config exists
    if not config.exists():
        click.secho("✗ No configuration found", fg="red")
        click.echo("Run 'drydocks setup' first")
        sys.exit(1)

    # Validate config
    valid, message = config.validate()
    if not valid:
        click.secho(f"✗ Configuration invalid: {message}", fg="red")
        sys.exit(1)

    # Create client
    client = LLMClient(
        endpoint=config.get("endpoint"),
        api_key=config.get("api_key"),
        timeout=config.get("timeout_seconds"),
        max_retries=config.get("max_retries"),
        retry_delay=config.get("retry_delay_seconds"),
    )

    # Discover tests
    runner = TestRunner()
    all_tests = runner.discover_tests()

    if not all_tests:
        click.secho("✗ No tests discovered", fg="red")
        sys.exit(1)

    # Select tests to run
    if test_name.lower() == "all":
        selected_tests = all_tests
    else:
        # Try to find matching test
        matching = {k: v for k, v in all_tests.items() if k.lower() == test_name.lower()}
        if not matching:
            click.secho(f"✗ Test '{test_name}' not found", fg="red")
            click.echo(f"Available: {', '.join(all_tests.keys())}")
            sys.exit(1)
        selected_tests = matching

    click.echo("")
    click.echo("=" * 60)
    click.echo(f"Running tests: {', '.join(selected_tests.keys())}")
    click.echo(f"Runs per test: {runs}")
    click.echo("=" * 60)
    click.echo("")

    # Run tests
    try:
        results = runner.run_suite(selected_tests, client, config, runs)
    except Exception as e:
        click.secho(f"✗ Test execution failed: {e}", fg="red")
        sys.exit(1)

    # Print results
    if verbose:
        click.echo(ReportFormatter.format_table(results))

    stats = runner.aggregate_results(results)
    click.echo(ReportFormatter.format_summary(stats))

    # Save results
    output_file = ReportFormatter.save_jsonl(results)
    click.echo(f"Results saved to: {output_file}")
    click.echo("")

    # Exit with appropriate code
    sys.exit(0 if stats["failed"] == 0 else 1)


@cli.command()
def reset():
    """Delete configuration file."""
    if not click.confirm("Delete DryDocks configuration?"):
        click.echo("Cancelled.")
        return

    config = ConfigManager()
    config.delete()
    click.echo("Configuration deleted.")


if __name__ == "__main__":
    cli()
