"""Reddit API client wrapper using PRAW."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import praw
from praw.models import Submission

from .config import RedditConfig
from .store.models import Post


class RedditClient:
    """Client for interacting with the Reddit API."""
    
    def __init__(self, config: RedditConfig, fixtures_path: Optional[Path] = None):
        """
        Initialize the Reddit client.
        
        Args:
            config: Reddit API configuration
            fixtures_path: Path to JSON fixtures for dry-run mode
        """
        self.config = config
        self.fixtures_path = fixtures_path
        self._reddit: Optional[praw.Reddit] = None
        
        if config.is_configured:
            self._reddit = praw.Reddit(
                client_id=config.client_id,
                client_secret=config.client_secret,
                user_agent=config.user_agent,
            )
    
    @property
    def is_live(self) -> bool:
        """Check if we're connected to the live Reddit API."""
        return self._reddit is not None
    
    def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        max_age_hours: int = 72,
    ) -> Iterator[Post]:
        """
        Fetch posts from a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit to fetch from
            limit: Maximum number of posts to fetch
            max_age_hours: Only include posts created within this many hours
            
        Yields:
            Post objects
        """
        if self._reddit:
            yield from self._fetch_live(subreddit_name, limit, max_age_hours)
        elif self.fixtures_path:
            yield from self._fetch_fixtures(subreddit_name)
        else:
            print(f"[DRY-RUN] Would fetch {limit} posts from r/{subreddit_name}")
    
    def _fetch_live(
        self,
        subreddit_name: str,
        limit: int,
        max_age_hours: int,
    ) -> Iterator[Post]:
        """Fetch posts from the live Reddit API."""
        subreddit = self._reddit.subreddit(subreddit_name)
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        for submission in subreddit.new(limit=limit):
            # Skip stickied posts
            if submission.stickied:
                continue
            
            # Skip posts older than max_age_hours
            if submission.created_utc < cutoff_time:
                continue
            
            yield self._submission_to_post(submission, subreddit_name)
    
    def _fetch_fixtures(self, subreddit_name: str) -> Iterator[Post]:
        """Load posts from JSON fixtures."""
        fixture_file = self.fixtures_path / f"{subreddit_name}.json"
        
        if not fixture_file.exists():
            print(f"[DRY-RUN] No fixture file found for r/{subreddit_name}")
            return
        
        with open(fixture_file) as f:
            posts_data = json.load(f)
        
        for data in posts_data:
            yield Post(
                reddit_id=data["id"],
                subreddit=subreddit_name,
                title=data["title"],
                selftext=data.get("selftext", ""),
                url=data["url"],
                author=data.get("author", "[deleted]"),
                created_utc=datetime.fromisoformat(data["created_utc"]),
                score=data.get("score", 0),
                num_comments=data.get("num_comments", 0),
            )
    
    def _submission_to_post(self, submission: Submission, subreddit_name: str) -> Post:
        """Convert a PRAW submission to our Post model."""
        return Post(
            reddit_id=submission.id,
            subreddit=subreddit_name,
            title=submission.title,
            selftext=submission.selftext or "",
            url=f"https://www.reddit.com{submission.permalink}",
            author=str(submission.author) if submission.author else "[deleted]",
            created_utc=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
            score=submission.score,
            num_comments=submission.num_comments,
        )

