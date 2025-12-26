#!/usr/bin/env python3
"""
Fetch posts from Reddit and send notifications.

This script is designed to be run via cron every 30 minutes:
    */30 * * * * cd /path/to/reddit_hirelab_listener && python scripts/run_fetch_and_notify.py

Or run manually:
    python scripts/run_fetch_and_notify.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config, DEFAULT_SUBREDDITS
from src.store import Database, PostStatus, Action, ActionType
from src.fetch import fetch_posts
from src.drafts import generate_drafts
from src.outputs import send_to_slack, write_to_sheets, print_to_console


def main():
    """Run fetch and notify workflow."""
    print("=" * 50)
    print("HireLab Reddit Listener - Fetch & Notify")
    print("=" * 50)
    
    # Load configuration
    reddit_config, slack_config, sheets_config, openai_config, app_config = load_config()
    
    # Initialize database
    db = Database(app_config.data_dir / "hirelab_reddit.sqlite")
    
    # Check Reddit configuration
    if not reddit_config.is_configured:
        print("\n⚠ Reddit API not configured")
        print("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
        print("Running in dry-run mode...\n")
        app_config.dry_run = True
    
    # Step 1: Fetch posts
    print("\n📥 Fetching posts from Reddit...")
    stats = fetch_posts(
        reddit_config=reddit_config,
        app_config=app_config,
        db=db,
        subreddits=DEFAULT_SUBREDDITS,
        verbose=True,
    )
    
    # Step 2: Get high-intent posts that need processing
    print("\n🎯 Finding high-intent posts...")
    posts = db.get_posts_by_status(
        statuses=[PostStatus.NEW, PostStatus.QUEUED],
        min_score=app_config.intent_score_threshold,
        limit=20,
    )
    
    if not posts:
        print("No new high-intent posts found.")
        return
    
    print(f"Found {len(posts)} posts above threshold")
    
    # Step 3: Generate drafts
    print("\n✍️ Generating draft replies...")
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
            print(f"  ✓ Generated drafts for {post.reddit_id}")
    
    # Step 4: Send to Slack
    if slack_config.is_configured:
        print("\n📤 Sending to Slack...")
        if send_to_slack(posts, slack_config):
            for post in posts:
                db.update_status(post.reddit_id, PostStatus.SENT)
                db.save_action(Action(
                    reddit_id=post.reddit_id,
                    action_type=ActionType.SENT_TO_SLACK,
                ))
            print("  ✓ Sent to Slack")
        else:
            print("  ✗ Failed to send to Slack")
    else:
        print("\n⚠ Slack not configured, printing to console...")
        print_to_console(posts)
    
    # Step 5: Write to Sheets/CSV
    csv_path = app_config.data_dir / "queue.csv"
    print("\n📝 Writing to Sheets/CSV...")
    if write_to_sheets(posts, sheets_config, csv_path):
        for post in posts:
            db.save_action(Action(
                reddit_id=post.reddit_id,
                action_type=ActionType.WRITTEN_TO_SHEETS,
            ))
        print("  ✓ Written to Sheets/CSV")
    
    print("\n✅ Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()

