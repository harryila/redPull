"""Slack output module."""

import json
from typing import Optional

import requests

from ..config import SlackConfig
from ..store.models import Post
from ..scoring import get_match_reasons


def send_to_slack(
    posts: list[Post],
    slack_config: SlackConfig,
    title: str = "🎯 HireLab Reddit Leads",
) -> bool:
    """
    Send posts to Slack via webhook.
    
    Args:
        posts: List of posts to send
        slack_config: Slack configuration
        title: Message title
        
    Returns:
        True if successful, False otherwise
    """
    if not slack_config.is_configured:
        print("[WARN] Slack not configured, skipping")
        return False
    
    if not posts:
        print("[INFO] No posts to send to Slack")
        return True
    
    # Build Slack blocks
    blocks = _build_slack_blocks(posts, title)
    
    try:
        response = requests.post(
            slack_config.webhook_url,
            json={"blocks": blocks},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Failed to send to Slack: {e}")
        return False


def _build_slack_blocks(posts: list[Post], title: str) -> list[dict]:
    """Build Slack block kit message."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title,
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Found *{len(posts)}* high-intent posts"
                }
            ]
        },
        {"type": "divider"},
    ]
    
    for post in posts[:10]:  # Limit to 10 posts per message
        blocks.extend(_build_post_blocks(post))
        blocks.append({"type": "divider"})
    
    # Add footer with CLI commands
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "📝 *Commands:* `hirelab mark-replied <id>` | `hirelab mark-skipped <id>`"
            }
        ]
    })
    
    return blocks


def _build_post_blocks(post: Post) -> list[dict]:
    """Build Slack blocks for a single post."""
    # Match reasons
    reasons = get_match_reasons(post)
    reasons_text = "\n".join(f"• {r}" for r in reasons) if reasons else "• Keyword match"
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{post.url}|{_escape_slack(post.title)}>*\n"
                        f"r/{post.subreddit} • Score: {post.intent_score:.0f} • "
                        f"👤 u/{post.author}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Why matched:*\n{reasons_text}"
                }
            ]
        },
    ]
    
    # Add Draft A
    if post.draft_a:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Draft A (no mention):*\n```{_truncate(post.draft_a, 500)}```"
            }
        })
    
    # Add Draft B if different and mention allowed
    if post.draft_b and post.mention_allowed and post.draft_b != post.draft_a:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Draft B (soft mention):*\n```{_truncate(post.draft_b, 500)}```"
            }
        })
    
    # Add action hint
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"ID: `{post.reddit_id}` | "
                        f"`hirelab mark-replied {post.reddit_id}` | "
                        f"`hirelab mark-skipped {post.reddit_id}`"
            }
        ]
    })
    
    return blocks


def _escape_slack(text: str) -> str:
    """Escape special characters for Slack."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def build_daily_digest(
    posts: list[Post],
    stats: dict,
) -> list[dict]:
    """Build a daily digest Slack message."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Daily Reddit Digest - HireLab",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary:*\n"
                        f"• Total posts tracked: {stats.get('total_posts', 0)}\n"
                        f"• New today: {stats.get('new_today', 0)}\n"
                        f"• Replied: {stats.get('replied', 0)}\n"
                        f"• Pending review: {len(posts)}"
            }
        },
        {"type": "divider"},
    ]
    
    if posts:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔥 Top 10 Posts by Intent Score:*"
            }
        })
        
        for i, post in enumerate(posts[:10], 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. <{post.url}|{_escape_slack(post.title)}>\n"
                            f"   r/{post.subreddit} • Score: {post.intent_score:.0f}"
                }
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No high-intent posts found today._"
            }
        })
    
    return blocks

