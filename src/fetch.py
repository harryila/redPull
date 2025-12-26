"""Fetch posts from Reddit subreddits."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DEFAULT_SUBREDDITS, AppConfig, RedditConfig
from .reddit_client import RedditClient
from .scoring import calculate_intent_score, check_mention_allowed
from .dedupe import compute_content_hash, is_duplicate
from .store import Database, Post, PostStatus, Action, ActionType

console = Console()


def fetch_posts(
    reddit_config: RedditConfig,
    app_config: AppConfig,
    db: Database,
    subreddits: Optional[list[str]] = None,
    verbose: bool = True,
) -> dict:
    """
    Fetch posts from Reddit, score them, dedupe, and store.
    
    Args:
        reddit_config: Reddit API configuration
        app_config: Application settings
        db: Database instance
        subreddits: Optional list of subreddits to fetch from (defaults to DEFAULT_SUBREDDITS)
        verbose: Whether to print progress
        
    Returns:
        Dictionary with fetch statistics
    """
    subreddits = subreddits or DEFAULT_SUBREDDITS
    client = RedditClient(
        config=reddit_config,
        fixtures_path=app_config.data_dir / "fixtures" if app_config.dry_run else None,
    )
    
    stats = {
        "total_fetched": 0,
        "new_posts": 0,
        "duplicates": 0,
        "above_threshold": 0,
        "by_subreddit": {},
    }
    
    if verbose:
        mode = "LIVE" if client.is_live else "DRY-RUN"
        console.print(f"\n[bold blue]Fetching posts ({mode} mode)[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=not verbose,
    ) as progress:
        for subreddit in subreddits:
            task = progress.add_task(f"r/{subreddit}...", total=None)
            subreddit_stats = {"fetched": 0, "new": 0, "duplicates": 0}
            
            for post in client.fetch_subreddit_posts(
                subreddit_name=subreddit,
                limit=app_config.posts_per_subreddit,
                max_age_hours=app_config.fetch_hours_lookback,
            ):
                stats["total_fetched"] += 1
                subreddit_stats["fetched"] += 1
                
                # Compute content hash
                post.content_hash = compute_content_hash(post.title, post.selftext)
                
                # Check for duplicate content
                existing_id = is_duplicate(db, post.reddit_id, post.content_hash)
                if existing_id:
                    stats["duplicates"] += 1
                    subreddit_stats["duplicates"] += 1
                    
                    # Record the duplicate
                    if not db.post_exists(post.reddit_id):
                        post.status = PostStatus.DUPLICATE
                        db.save_post(post)
                        db.save_action(Action(
                            reddit_id=post.reddit_id,
                            action_type=ActionType.MARK_SKIPPED,
                            notes=f"Duplicate of {existing_id}",
                        ))
                    continue
                
                # Calculate intent score
                score_result = calculate_intent_score(
                    title=post.title,
                    selftext=post.selftext,
                    subreddit=subreddit,
                    score=post.score,
                    num_comments=post.num_comments,
                )
                
                post.intent_score = score_result["score"]
                post.matched_keywords = score_result["matched_keywords"]
                post.mention_allowed = check_mention_allowed(
                    post.title,
                    post.selftext,
                    subreddit,
                )
                
                # Determine status
                if db.post_exists(post.reddit_id):
                    # Update existing post
                    db.save_post(post)
                else:
                    # New post
                    stats["new_posts"] += 1
                    subreddit_stats["new"] += 1
                    
                    if post.intent_score >= app_config.intent_score_threshold:
                        post.status = PostStatus.QUEUED
                        stats["above_threshold"] += 1
                    else:
                        post.status = PostStatus.NEW
                    
                    db.save_post(post)
                
                progress.update(task, description=f"r/{subreddit} ({subreddit_stats['fetched']} posts)")
            
            stats["by_subreddit"][subreddit] = subreddit_stats
            progress.update(task, completed=True)
    
    if verbose:
        console.print(f"\n[green]✓[/green] Fetched {stats['total_fetched']} posts")
        console.print(f"  • New: {stats['new_posts']}")
        console.print(f"  • Duplicates: {stats['duplicates']}")
        console.print(f"  • Above threshold: {stats['above_threshold']}")
    
    return stats

