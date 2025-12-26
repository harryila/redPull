#!/usr/bin/env python3
"""
Generate and send a daily digest of top posts.

This script is designed to be run via cron once daily at 9am:
    0 9 * * * cd /path/to/reddit_hirelab_listener && python scripts/run_daily_digest.py

Or run manually:
    python scripts/run_daily_digest.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from src.config import load_config
from src.store import Database, PostStatus
from src.outputs.slack import build_daily_digest


def main():
    """Run daily digest workflow."""
    print("=" * 50)
    print("HireLab Reddit Listener - Daily Digest")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Load configuration
    _, slack_config, _, _, app_config = load_config()
    
    # Initialize database
    db = Database(app_config.data_dir / "hirelab_reddit.sqlite")
    
    # Get stats
    db_stats = db.get_stats()
    
    # Get top posts from last 24 hours
    print("\n📊 Generating daily digest...")
    posts = db.get_recent_posts(hours=24, limit=10)
    
    # Calculate additional stats
    stats = {
        "total_posts": db_stats.get("total_posts", 0),
        "new_today": len(posts),
        "replied": db_stats.get("by_status", {}).get("REPLIED", 0),
    }
    
    print(f"  Posts tracked: {stats['total_posts']}")
    print(f"  New in last 24h: {stats['new_today']}")
    print(f"  Total replied: {stats['replied']}")
    
    if not slack_config.is_configured:
        print("\n⚠ Slack not configured")
        print("Set SLACK_WEBHOOK_URL in .env to receive daily digests")
        
        # Print to console instead
        print("\n📋 Top 10 Posts (Last 24 Hours):")
        for i, post in enumerate(posts[:10], 1):
            print(f"\n{i}. [{post.intent_score:.0f}] r/{post.subreddit}")
            print(f"   {post.title[:60]}...")
            print(f"   {post.url}")
        
        return
    
    # Build and send Slack message
    print("\n📤 Sending daily digest to Slack...")
    blocks = build_daily_digest(posts, stats)
    
    try:
        response = requests.post(
            slack_config.webhook_url,
            json={"blocks": blocks},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        print("  ✓ Daily digest sent to Slack")
    except requests.RequestException as e:
        print(f"  ✗ Failed to send: {e}")
    
    print("\n✅ Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()

