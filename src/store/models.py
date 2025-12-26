"""Data models for the Reddit listener."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class PostStatus(str, Enum):
    """Status of a Reddit post in our system."""
    NEW = "NEW"
    QUEUED = "QUEUED"
    SENT = "SENT"
    REPLIED = "REPLIED"
    SKIPPED = "SKIPPED"
    DUPLICATE = "DUPLICATE"


class ActionType(str, Enum):
    """Types of actions that can be taken on a post."""
    DRAFTED = "DRAFTED"
    SENT_TO_SLACK = "SENT_TO_SLACK"
    WRITTEN_TO_SHEETS = "WRITTEN_TO_SHEETS"
    MARK_REPLIED = "MARK_REPLIED"
    MARK_SKIPPED = "MARK_SKIPPED"


@dataclass
class Post:
    """Represents a Reddit post."""
    reddit_id: str
    subreddit: str
    title: str
    selftext: str
    url: str
    author: str
    created_utc: datetime
    score: int
    num_comments: int
    matched_keywords: list[str] = field(default_factory=list)
    intent_score: float = 0.0
    status: PostStatus = PostStatus.NEW
    last_seen_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    id: Optional[int] = None
    draft_a: str = ""
    draft_b: str = ""
    mention_allowed: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "reddit_id": self.reddit_id,
            "subreddit": self.subreddit,
            "title": self.title,
            "selftext": self.selftext,
            "url": self.url,
            "author": self.author,
            "created_utc": self.created_utc.isoformat(),
            "score": self.score,
            "num_comments": self.num_comments,
            "matched_keywords": json.dumps(self.matched_keywords),
            "intent_score": self.intent_score,
            "status": self.status.value,
            "last_seen_at": self.last_seen_at.isoformat(),
            "content_hash": self.content_hash,
            "draft_a": self.draft_a,
            "draft_b": self.draft_b,
            "mention_allowed": int(self.mention_allowed),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            reddit_id=data["reddit_id"],
            subreddit=data["subreddit"],
            title=data["title"],
            selftext=data["selftext"],
            url=data["url"],
            author=data["author"],
            created_utc=datetime.fromisoformat(data["created_utc"]) if isinstance(data["created_utc"], str) else data["created_utc"],
            score=data["score"],
            num_comments=data["num_comments"],
            matched_keywords=json.loads(data["matched_keywords"]) if isinstance(data["matched_keywords"], str) else data["matched_keywords"],
            intent_score=data["intent_score"],
            status=PostStatus(data["status"]),
            last_seen_at=datetime.fromisoformat(data["last_seen_at"]) if isinstance(data["last_seen_at"], str) else data["last_seen_at"],
            content_hash=data["content_hash"],
            draft_a=data.get("draft_a", ""),
            draft_b=data.get("draft_b", ""),
            mention_allowed=bool(data.get("mention_allowed", False)),
        )


@dataclass
class Action:
    """Represents an action taken on a post."""
    reddit_id: str
    action_type: ActionType
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "reddit_id": self.reddit_id,
            "action_type": self.action_type.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            reddit_id=data["reddit_id"],
            action_type=ActionType(data["action_type"]),
            notes=data["notes"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
        )

