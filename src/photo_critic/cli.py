"""CLI entry point for photo-critic."""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from photo_critic.batch import BatchClient
from photo_critic.discovery import discover_images, get_image_stats
from photo_critic.prepare import DEFAULT_OPENAI_MODEL, prepare_batch
from photo_critic.report import generate_report

# Set up rich console
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler.

    Args:
        verbose: If True, set log level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("./critic-report.json"),
    help="Output file path",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "both"], case_sensitive=False),
    default="json",
    help="Output format",
)
@click.option(
    "--min-score",
    type=float,
    default=0.0,
    help="Only include images above this score",
)
@click.option(
    "--provider",
    type=click.Choice(["openai"], case_sensitive=False),
    default="openai",
    help="API provider to use (OpenAI only for now)",
)
@click.option(
    "--model",
    type=str,
    default=None,
    show_default="provider default",
    help="Model to use (provider-specific)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without calling API",
)
@click.option(
    "--max-images",
    type=int,
    default=100,
    help="Limit number of images to process",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Include subdirectories",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    path: Path,
    output: Path,
    format: str,
    min_score: float,
    provider: str,
    model: str,
    dry_run: bool,
    max_images: int,
    recursive: bool,
    verbose: bool,
) -> None:
    """Photo Critic - AI-powered batch photo criticism using vision APIs.

    Analyze a folder of images and generate detailed critiques with scores.

    Examples:

        \b
        # Basic usage
        $ photo-critic ./photos

        \b
        # Generate markdown report
        $ photo-critic ./photos --format markdown --output results.md

        \b
        # Only include photos scoring 7 or higher
        $ photo-critic ./photos --min-score 7.0

        \b
        # Dry run to see what would be processed
        $ photo-critic ./photos --dry-run

        \b
        # Use OpenAI Batch API
        $ photo-critic ./photos --provider openai --model gpt-4o-mini
    """
    load_dotenv()
    setup_logging(verbose)

    provider = provider.lower()
    if model is None:
        model = DEFAULT_OPENAI_MODEL

    console.print(
        "\n[bold cyan]Photo Critic[/bold cyan] - AI Photo Analysis "
        f"[dim]({provider})[/dim]\n"
    )

    # 1. Discovery Phase
    console.print("[bold]1. Discovering images...[/bold]")

    try:
        images = discover_images(path, recursive=recursive, max_images=max_images)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    if not images:
        console.print("[yellow]No images found.[/yellow]")
        sys.exit(0)

    # Show discovery stats
    stats = get_image_stats(images)
    table = Table(title="Discovery Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Images", str(stats["total"]))
    table.add_row("Total Size", f"{stats['total_size_mb']} MB")
    table.add_row("Average Size", f"{stats['avg_size_mb']} MB")

    for ext, count in stats["by_extension"].items():
        table.add_row(f"  {ext}", str(count))

    console.print(table)

    # Dry run - stop here
    if dry_run:
        console.print("\n[yellow]Dry run - stopping here.[/yellow]")
        console.print(f"\nWould process {len(images)} images:")
        for img in images[:10]:  # Show first 10
            console.print(f"  - {img.name}")
        if len(images) > 10:
            console.print(f"  ... and {len(images) - 10} more")
        sys.exit(0)

    # 2. Preparation Phase
    console.print("\n[bold]2. Preparing batch...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing images...", total=None)

        try:
            batch_requests, image_metadata = prepare_batch(
                images, model=model, provider=provider
            )
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

        progress.update(task, completed=True)

    console.print(f"[green]Prepared {len(batch_requests)} requests[/green]")

    if not batch_requests:
        console.print("[yellow]No images could be processed.[/yellow]")
        sys.exit(0)

    # Estimate cost
    console.print(
        "\n[dim]Estimated cost: see OpenAI pricing for your model.[/dim]"
    )

    # 3. Batch Submission
    console.print("\n[bold]3. Submitting batch...[/bold]")

    try:
        client = BatchClient(provider=provider)
        batch_id = client.submit_batch(batch_requests)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    console.print(f"[green]Batch submitted:[/green] {batch_id}")

    # 4. Polling
    console.print("\n[bold]4. Waiting for results...[/bold]")
    console.print(
        "[dim]This may take several minutes. "
        "You can safely cancel and resume later.[/dim]\n"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing batch...", total=None)

            status = client.poll_batch(batch_id, poll_interval=30)

            progress.update(task, completed=True)

        # Show final status
        counts = status["request_counts"]
        console.print(
            f"\n[green]Batch complete![/green] "
            f"{counts['succeeded']} succeeded, "
            f"{counts['errored']} errored"
        )

    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]Interrupted.[/yellow] Batch ID: {batch_id}\n"
            "You can retrieve results later using this batch ID."
        )
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print(f"\nBatch ID: {batch_id}")
        sys.exit(1)

    # 5. Get Results
    console.print("\n[bold]5. Retrieving results...[/bold]")

    try:
        batch_results = client.get_batch_results(batch_id)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    console.print(f"[green]Retrieved {len(batch_results)} results[/green]")

    # 6. Generate Report
    console.print("\n[bold]6. Generating report...[/bold]")

    try:
        generate_report(
            batch_results,
            image_metadata,
            output,
            format=format,
            min_score=min_score,
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    # Success!
    console.print("\n[bold green]✓ Complete![/bold green]")

    if format == "json":
        console.print(f"Report saved to: [cyan]{output.with_suffix('.json')}[/cyan]")
    elif format == "markdown":
        console.print(f"Report saved to: [cyan]{output.with_suffix('.md')}[/cyan]")
    else:  # both
        console.print(
            f"Reports saved to:\n"
            f"  - [cyan]{output.with_suffix('.json')}[/cyan]\n"
            f"  - [cyan]{output.with_suffix('.md')}[/cyan]"
        )

    console.print()


if __name__ == "__main__":
    main()
