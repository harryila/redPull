"""SQLite database management."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Post, Action, PostStatus, ActionType


class Database:
    """SQLite database for storing posts and actions."""
    
    def __init__(self, db_path: Path):
        """Initialize database connection."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reddit_id TEXT UNIQUE NOT NULL,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    selftext TEXT,
                    url TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    num_comments INTEGER DEFAULT 0,
                    matched_keywords TEXT DEFAULT '[]',
                    intent_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'NEW',
                    last_seen_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    draft_a TEXT DEFAULT '',
                    draft_b TEXT DEFAULT '',
                    mention_allowed INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reddit_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (reddit_id) REFERENCES posts(reddit_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_reddit_id ON posts(reddit_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_reddit_id ON actions(reddit_id)")
            
            conn.commit()
    
    def post_exists(self, reddit_id: str) -> bool:
        """Check if a post already exists by reddit_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM posts WHERE reddit_id = ?",
                (reddit_id,)
            )
            return cursor.fetchone() is not None
    
    def hash_exists(self, content_hash: str) -> Optional[str]:
        """Check if a content hash already exists. Returns reddit_id if found."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT reddit_id FROM posts WHERE content_hash = ?",
                (content_hash,)
            )
            row = cursor.fetchone()
            return row["reddit_id"] if row else None
    
    def save_post(self, post: Post) -> int:
        """Save or update a post."""
        with self._get_connection() as conn:
            data = post.to_dict()
            
            # Check if post exists
            if self.post_exists(post.reddit_id):
                # Update existing post
                conn.execute("""
                    UPDATE posts SET
                        score = ?,
                        num_comments = ?,
                        intent_score = ?,
                        last_seen_at = ?,
                        draft_a = ?,
                        draft_b = ?,
                        mention_allowed = ?
                    WHERE reddit_id = ?
                """, (
                    data["score"],
                    data["num_comments"],
                    data["intent_score"],
                    data["last_seen_at"],
                    data["draft_a"],
                    data["draft_b"],
                    data["mention_allowed"],
                    data["reddit_id"],
                ))
            else:
                # Insert new post
                conn.execute("""
                    INSERT INTO posts (
                        reddit_id, subreddit, title, selftext, url, author,
                        created_utc, score, num_comments, matched_keywords,
                        intent_score, status, last_seen_at, content_hash,
                        draft_a, draft_b, mention_allowed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["reddit_id"],
                    data["subreddit"],
                    data["title"],
                    data["selftext"],
                    data["url"],
                    data["author"],
                    data["created_utc"],
                    data["score"],
                    data["num_comments"],
                    data["matched_keywords"],
                    data["intent_score"],
                    data["status"],
                    data["last_seen_at"],
                    data["content_hash"],
                    data["draft_a"],
                    data["draft_b"],
                    data["mention_allowed"],
                ))
            
            conn.commit()
            cursor = conn.execute(
                "SELECT id FROM posts WHERE reddit_id = ?",
                (post.reddit_id,)
            )
            return cursor.fetchone()["id"]
    
    def get_post(self, reddit_id: str) -> Optional[Post]:
        """Get a post by reddit_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM posts WHERE reddit_id = ?",
                (reddit_id,)
            )
            row = cursor.fetchone()
            if row:
                return Post.from_dict(dict(row))
            return None
    
    def get_posts_by_status(
        self,
        statuses: list[PostStatus],
        min_score: Optional[float] = None,
        limit: int = 100
    ) -> list[Post]:
        """Get posts filtered by status and minimum score."""
        with self._get_connection() as conn:
            status_placeholders = ",".join("?" * len(statuses))
            query = f"""
                SELECT * FROM posts 
                WHERE status IN ({status_placeholders})
            """
            params: list = [s.value for s in statuses]
            
            if min_score is not None:
                query += " AND intent_score >= ?"
                params.append(min_score)
            
            query += " ORDER BY intent_score DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [Post.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def update_status(self, reddit_id: str, status: PostStatus) -> bool:
        """Update the status of a post."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE posts SET status = ? WHERE reddit_id = ?",
                (status.value, reddit_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def save_action(self, action: Action) -> int:
        """Save an action."""
        with self._get_connection() as conn:
            data = action.to_dict()
            cursor = conn.execute("""
                INSERT INTO actions (reddit_id, action_type, notes, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                data["reddit_id"],
                data["action_type"],
                data["notes"],
                data["created_at"],
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_actions(self, reddit_id: str) -> list[Action]:
        """Get all actions for a post."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM actions WHERE reddit_id = ? ORDER BY created_at DESC",
                (reddit_id,)
            )
            return [Action.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_recent_posts(self, hours: int = 24, limit: int = 50) -> list[Post]:
        """Get recent posts from the last N hours."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM posts 
                WHERE datetime(created_utc) >= datetime('now', ?)
                ORDER BY intent_score DESC
                LIMIT ?
            """, (f"-{hours} hours", limit))
            return [Post.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}
            
            # Count by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM posts GROUP BY status
            """)
            stats["by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # Total posts
            cursor = conn.execute("SELECT COUNT(*) as count FROM posts")
            stats["total_posts"] = cursor.fetchone()["count"]
            
            # Total actions
            cursor = conn.execute("SELECT COUNT(*) as count FROM actions")
            stats["total_actions"] = cursor.fetchone()["count"]
            
            return stats

