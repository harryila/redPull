"""Deduplication logic for Reddit posts."""

import hashlib
import re
from typing import Optional

from .store import Database


def normalize_for_hash(text: str) -> str:
    """
    Normalize text for hashing.
    
    - Lowercase
    - Remove punctuation
    - Collapse whitespace
    - Truncate to first 500 chars (after normalization)
    """
    # Lowercase
    text = text.lower()
    
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate
    return text[:500]


def compute_content_hash(title: str, selftext: str) -> str:
    """
    Compute a content hash for deduplication.
    
    Uses normalized title + first 500 chars of normalized selftext.
    """
    normalized_title = normalize_for_hash(title)
    normalized_selftext = normalize_for_hash(selftext)
    
    combined = f"{normalized_title}|{normalized_selftext}"
    
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def is_duplicate(
    db: Database,
    reddit_id: str,
    content_hash: str,
) -> Optional[str]:
    """
    Check if a post is a duplicate.
    
    A post is considered duplicate if:
    1. The reddit_id already exists (same post)
    2. The content_hash matches another post (same content, different ID)
    
    Args:
        db: Database instance
        reddit_id: The Reddit post ID
        content_hash: The computed content hash
        
    Returns:
        The reddit_id of the existing post if duplicate, None otherwise
    """
    # Check if this exact post already exists
    if db.post_exists(reddit_id):
        return reddit_id
    
    # Check if content hash exists (indicates repost or cross-post)
    existing_id = db.hash_exists(content_hash)
    if existing_id and existing_id != reddit_id:
        return existing_id
    
    return None

