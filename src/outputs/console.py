"""Console output module using Rich."""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from ..store.models import Post, PostStatus
from ..scoring import get_match_reasons


console = Console()


def print_to_console(
    posts: list[Post],
    title: str = "🎯 HireLab Reddit Leads",
    show_drafts: bool = True,
) -> None:
    """
    Print posts to console using Rich formatting.
    
    Args:
        posts: List of posts to display
        title: Header title
        show_drafts: Whether to show draft replies
    """
    if not posts:
        console.print("\n[yellow]No posts to display.[/yellow]\n")
        return
    
    console.print(f"\n[bold blue]{title}[/bold blue]")
    console.print(f"[dim]Found {len(posts)} high-intent posts[/dim]\n")
    
    for i, post in enumerate(posts, 1):
        _print_post(post, i, show_drafts)
    
    # Print CLI commands reference
    console.print("\n[bold]Commands:[/bold]")
    console.print("  [cyan]hirelab mark-replied <reddit_id>[/cyan] - Mark as replied")
    console.print("  [cyan]hirelab mark-skipped <reddit_id>[/cyan] - Skip this post")
    console.print()


def _print_post(post: Post, index: int, show_drafts: bool = True) -> None:
    """Print a single post with rich formatting."""
    # Build header
    status_color = _get_status_color(post.status)
    header = f"[{index}] r/{post.subreddit} • Score: {post.intent_score:.0f} • {post.status.value}"
    
    # Match reasons
    reasons = get_match_reasons(post)
    reasons_text = " • ".join(reasons) if reasons else "Keyword match"
    
    # Build content
    content = Text()
    content.append(f"Title: ", style="bold")
    content.append(f"{post.title}\n", style="white")
    content.append(f"Author: ", style="dim")
    content.append(f"u/{post.author}\n", style="cyan")
    content.append(f"URL: ", style="dim")
    content.append(f"{post.url}\n", style="blue underline")
    content.append(f"Why: ", style="dim")
    content.append(f"{reasons_text}\n", style="yellow")
    content.append(f"ID: ", style="dim")
    content.append(f"{post.reddit_id}", style="green")
    
    panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style=status_color,
    )
    console.print(panel)
    
    # Show drafts if available and requested
    if show_drafts and (post.draft_a or post.draft_b):
        _print_drafts(post)
    
    console.print()


def _print_drafts(post: Post) -> None:
    """Print draft replies for a post."""
    if post.draft_a:
        console.print("  [bold green]Draft A (no mention):[/bold green]")
        # Indent the draft
        for line in post.draft_a.split("\n"):
            console.print(f"    {line}")
    
    if post.draft_b and post.mention_allowed and post.draft_b != post.draft_a:
        console.print()
        console.print("  [bold yellow]Draft B (soft mention):[/bold yellow]")
        for line in post.draft_b.split("\n"):
            console.print(f"    {line}")


def _get_status_color(status: PostStatus) -> str:
    """Get color for a status."""
    return {
        PostStatus.NEW: "blue",
        PostStatus.QUEUED: "yellow",
        PostStatus.SENT: "cyan",
        PostStatus.REPLIED: "green",
        PostStatus.SKIPPED: "dim",
        PostStatus.DUPLICATE: "red",
    }.get(status, "white")


def print_stats(stats: dict) -> None:
    """Print database statistics."""
    table = Table(title="📊 Database Statistics")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    for status, count in stats.get("by_status", {}).items():
        table.add_row(status, str(count))
    
    table.add_section()
    table.add_row("Total Posts", str(stats.get("total_posts", 0)), style="bold")
    table.add_row("Total Actions", str(stats.get("total_actions", 0)), style="bold")
    
    console.print(table)


def print_post_list(posts: list[Post]) -> None:
    """Print a compact list of posts."""
    table = Table(title="Posts")
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Score", justify="right", style="yellow", width=6)
    table.add_column("Subreddit", style="green", width=20)
    table.add_column("Status", width=10)
    table.add_column("Title", overflow="ellipsis")
    
    for i, post in enumerate(posts, 1):
        status_color = _get_status_color(post.status)
        table.add_row(
            str(i),
            post.reddit_id,
            f"{post.intent_score:.0f}",
            f"r/{post.subreddit}",
            Text(post.status.value, style=status_color),
            post.title[:60] + ("..." if len(post.title) > 60 else ""),
        )
    
    console.print(table)


def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    response = console.input(f"[yellow]{message} (y/n): [/yellow]")
    return response.lower() in ("y", "yes")

