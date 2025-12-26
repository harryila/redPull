"""Command-line interface for the Reddit HireLab Listener."""

import click
from pathlib import Path
from datetime import datetime

from rich.console import Console

from .config import load_config, DEFAULT_SUBREDDITS
from .store import Database, PostStatus, Action, ActionType
from .fetch import fetch_posts
from .drafts import generate_drafts
from .outputs import send_to_slack, write_to_sheets, print_to_console
from .outputs.console import print_stats, print_post_list

console = Console()


def get_db() -> Database:
    """Get database instance."""
    _, _, _, _, app_config = load_config()
    return Database(app_config.data_dir / "hirelab_reddit.sqlite")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """HireLab Reddit Listener - Discover and draft Reddit engagement opportunities."""
    pass


@cli.command()
@click.option("--subreddits", "-s", multiple=True, help="Specific subreddits to fetch (can be repeated)")
@click.option("--verbose/--quiet", "-v/-q", default=True, help="Show progress output")
def fetch(subreddits: tuple, verbose: bool):
    """Fetch posts from Reddit, score them, and store in database."""
    reddit_config, _, _, _, app_config = load_config()
    db = get_db()
    
    subs = list(subreddits) if subreddits else DEFAULT_SUBREDDITS
    
    if not reddit_config.is_configured:
        console.print("[yellow]⚠ Reddit API not configured - running in dry-run mode[/yellow]")
        app_config.dry_run = True
    
    stats = fetch_posts(
        reddit_config=reddit_config,
        app_config=app_config,
        db=db,
        subreddits=subs,
        verbose=verbose,
    )
    
    if verbose:
        console.print("\n[bold green]✓ Fetch complete![/bold green]")


@cli.command()
@click.option("--min-score", "-m", default=None, type=float, help="Minimum intent score (default: from config)")
@click.option("--limit", "-l", default=20, help="Maximum posts to include")
@click.option("--slack/--no-slack", default=True, help="Send to Slack")
@click.option("--sheets/--no-sheets", default=True, help="Write to Google Sheets")
@click.option("--generate-drafts/--no-drafts", "gen_drafts", default=True, help="Generate reply drafts")
def digest(min_score: float, limit: int, slack: bool, sheets: bool, gen_drafts: bool):
    """Generate and send digest of high-intent posts."""
    reddit_config, slack_config, sheets_config, openai_config, app_config = load_config()
    db = get_db()
    
    threshold = min_score if min_score is not None else app_config.intent_score_threshold
    
    # Get posts that are NEW or QUEUED and haven't been sent yet
    posts = db.get_posts_by_status(
        statuses=[PostStatus.NEW, PostStatus.QUEUED],
        min_score=threshold,
        limit=limit,
    )
    
    if not posts:
        console.print("[yellow]No new high-intent posts found.[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(posts)} posts above threshold ({threshold})[/bold]\n")
    
    # Generate drafts if requested
    if gen_drafts:
        console.print("[dim]Generating drafts...[/dim]")
        for post in posts:
            if not post.draft_a:
                draft_a, draft_b = generate_drafts(post, openai_config)
                post.draft_a = draft_a
                post.draft_b = draft_b
                db.save_post(post)
                db.save_action(Action(
                    reddit_id=post.reddit_id,
                    action_type=ActionType.DRAFTED,
                ))
    
    # Always print to console
    print_to_console(posts, show_drafts=gen_drafts)
    
    # Send to Slack if configured and requested
    if slack and slack_config.is_configured:
        console.print("[dim]Sending to Slack...[/dim]")
        if send_to_slack(posts, slack_config):
            for post in posts:
                db.update_status(post.reddit_id, PostStatus.SENT)
                db.save_action(Action(
                    reddit_id=post.reddit_id,
                    action_type=ActionType.SENT_TO_SLACK,
                ))
            console.print("[green]✓ Sent to Slack[/green]")
    
    # Write to Sheets if configured and requested
    if sheets:
        csv_fallback = app_config.data_dir / "queue.csv"
        console.print("[dim]Writing to Sheets/CSV...[/dim]")
        if write_to_sheets(posts, sheets_config, csv_fallback):
            for post in posts:
                db.save_action(Action(
                    reddit_id=post.reddit_id,
                    action_type=ActionType.WRITTEN_TO_SHEETS,
                ))
            console.print("[green]✓ Written to Sheets/CSV[/green]")


@cli.command("mark-replied")
@click.argument("reddit_id")
@click.option("--notes", "-n", default="", help="Optional notes about the reply")
def mark_replied(reddit_id: str, notes: str):
    """Mark a post as replied to."""
    db = get_db()
    
    post = db.get_post(reddit_id)
    if not post:
        console.print(f"[red]Post not found: {reddit_id}[/red]")
        return
    
    db.update_status(reddit_id, PostStatus.REPLIED)
    db.save_action(Action(
        reddit_id=reddit_id,
        action_type=ActionType.MARK_REPLIED,
        notes=notes,
    ))
    
    console.print(f"[green]✓ Marked {reddit_id} as REPLIED[/green]")


@cli.command("mark-skipped")
@click.argument("reddit_id")
@click.option("--notes", "-n", default="", help="Optional reason for skipping")
def mark_skipped(reddit_id: str, notes: str):
    """Mark a post as skipped (won't appear in future digests)."""
    db = get_db()
    
    post = db.get_post(reddit_id)
    if not post:
        console.print(f"[red]Post not found: {reddit_id}[/red]")
        return
    
    db.update_status(reddit_id, PostStatus.SKIPPED)
    db.save_action(Action(
        reddit_id=reddit_id,
        action_type=ActionType.MARK_SKIPPED,
        notes=notes,
    ))
    
    console.print(f"[yellow]✓ Marked {reddit_id} as SKIPPED[/yellow]")


@cli.command("list")
@click.option("--status", "-s", type=click.Choice(["NEW", "QUEUED", "SENT", "REPLIED", "SKIPPED", "DUPLICATE"]), 
              multiple=True, default=["NEW", "QUEUED"], help="Filter by status")
@click.option("--min-score", "-m", type=float, default=None, help="Minimum intent score")
@click.option("--limit", "-l", default=50, help="Maximum posts to show")
def list_posts(status: tuple, min_score: float, limit: int):
    """List posts from the database."""
    db = get_db()
    
    statuses = [PostStatus(s) for s in status]
    posts = db.get_posts_by_status(
        statuses=statuses,
        min_score=min_score,
        limit=limit,
    )
    
    if not posts:
        console.print("[yellow]No posts found matching criteria.[/yellow]")
        return
    
    print_post_list(posts)


@cli.command()
def stats():
    """Show database statistics."""
    db = get_db()
    db_stats = db.get_stats()
    print_stats(db_stats)


@cli.command()
@click.argument("reddit_id")
@click.option("--show-drafts/--no-drafts", default=True, help="Show draft replies")
def show(reddit_id: str, show_drafts: bool):
    """Show details for a specific post."""
    db = get_db()
    
    post = db.get_post(reddit_id)
    if not post:
        console.print(f"[red]Post not found: {reddit_id}[/red]")
        return
    
    print_to_console([post], show_drafts=show_drafts)
    
    # Show actions
    actions = db.get_actions(reddit_id)
    if actions:
        console.print("\n[bold]Action History:[/bold]")
        for action in actions:
            console.print(f"  • {action.action_type.value} at {action.created_at}")
            if action.notes:
                console.print(f"    Notes: {action.notes}")


@cli.command()
@click.argument("reddit_id")
def regenerate(reddit_id: str):
    """Regenerate drafts for a specific post."""
    _, _, _, openai_config, _ = load_config()
    db = get_db()
    
    post = db.get_post(reddit_id)
    if not post:
        console.print(f"[red]Post not found: {reddit_id}[/red]")
        return
    
    console.print("[dim]Regenerating drafts...[/dim]")
    draft_a, draft_b = generate_drafts(post, openai_config)
    post.draft_a = draft_a
    post.draft_b = draft_b
    db.save_post(post)
    db.save_action(Action(
        reddit_id=reddit_id,
        action_type=ActionType.DRAFTED,
        notes="Regenerated",
    ))
    
    console.print("[green]✓ Drafts regenerated[/green]\n")
    print_to_console([post], show_drafts=True)


if __name__ == "__main__":
    cli()

