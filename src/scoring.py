"""Intent scoring for Reddit posts."""

import math
import re
from typing import Optional

from .config import (
    POSITIVE_KEYWORDS,
    HIGH_INTENT_PHRASES,
    NEGATIVE_KEYWORDS,
    SUBREDDIT_WEIGHTS,
    MENTION_ALLOWED_PHRASES,
)


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def calculate_intent_score(
    title: str,
    selftext: str,
    subreddit: str,
    score: int,
    num_comments: int,
) -> dict:
    """
    Calculate an intent score for a Reddit post.
    
    Scoring breakdown:
    - Keyword matches: +5 each, capped at +40
    - High-intent phrases: +10 each, capped at +30
    - Subreddit weight multiplier
    - Engagement bonus: log1p(score + num_comments) * 3, capped at +15
    - Negative keyword penalty: -15 each, capped at -30
    - Short selftext penalty: -10 if < 20 chars
    
    Returns:
        Dictionary with score and metadata
    """
    combined_text = normalize_text(f"{title} {selftext}")
    
    # Track matched keywords
    matched_keywords = []
    
    # Base score
    intent_score = 0.0
    
    # Keyword matches (+5 each, cap at +40)
    keyword_score = 0
    for keyword in POSITIVE_KEYWORDS:
        if keyword.lower() in combined_text:
            keyword_score += 5
            matched_keywords.append(keyword)
    keyword_score = min(keyword_score, 40)
    intent_score += keyword_score
    
    # High-intent phrases (+10 each, cap at +30)
    phrase_score = 0
    matched_phrases = []
    for phrase in HIGH_INTENT_PHRASES:
        if phrase.lower() in combined_text:
            phrase_score += 10
            matched_phrases.append(phrase)
    phrase_score = min(phrase_score, 30)
    intent_score += phrase_score
    matched_keywords.extend(matched_phrases)
    
    # Subreddit weight multiplier
    subreddit_weight = SUBREDDIT_WEIGHTS.get(subreddit, 1.0)
    intent_score *= subreddit_weight
    
    # Engagement bonus (log1p(score + num_comments) * 3, cap at +15)
    engagement_score = min(math.log1p(score + num_comments) * 3, 15)
    intent_score += engagement_score
    
    # Negative keyword penalty (-15 each, cap at -30)
    negative_score = 0
    for keyword in NEGATIVE_KEYWORDS:
        if keyword.lower() in combined_text:
            negative_score -= 15
    negative_score = max(negative_score, -30)
    intent_score += negative_score
    
    # Short selftext penalty
    if len(selftext.strip()) < 20:
        intent_score -= 10
    
    # Clamp to 0-100
    intent_score = max(0, min(100, intent_score))
    
    return {
        "score": round(intent_score, 2),
        "matched_keywords": list(set(matched_keywords)),
        "subreddit_weight": subreddit_weight,
        "engagement_bonus": round(engagement_score, 2),
        "had_negative_keywords": negative_score < 0,
    }


def check_mention_allowed(
    title: str,
    selftext: str,
    subreddit: str,
) -> bool:
    """
    Determine if mentioning HireLab is appropriate.
    
    Allowed when:
    - Post mentions ATS, resume parser, keyword optimization, formatting, tailoring
    - User asks explicitly for tool recommendations
    
    Not allowed when:
    - Subreddit is recruitinghell
    - Post tone is hostile to tools/spam
    - Contains spam/promotion keywords
    """
    combined_text = normalize_text(f"{title} {selftext}")
    
    # Never mention in recruitinghell
    if subreddit.lower() == "recruitinghell":
        return False
    
    # Check for hostile/spam indicators
    hostile_indicators = ["spam", "promotion", "sick of", "hate these", "stop promoting"]
    for indicator in hostile_indicators:
        if indicator in combined_text:
            return False
    
    # Check for tool-request indicators
    for phrase in MENTION_ALLOWED_PHRASES:
        if phrase.lower() in combined_text:
            return True
    
    return False


def get_match_reasons(post) -> list[str]:
    """Generate human-readable reasons why a post matched."""
    reasons = []
    
    if post.matched_keywords:
        keywords = post.matched_keywords[:5]  # Limit to 5
        reasons.append(f"Keywords: {', '.join(keywords)}")
    
    # Subreddit context
    weight = SUBREDDIT_WEIGHTS.get(post.subreddit, 1.0)
    if weight > 1.0:
        reasons.append(f"High-value subreddit (r/{post.subreddit})")
    
    # Engagement
    if post.score > 10 or post.num_comments > 5:
        reasons.append(f"Engagement: {post.score} upvotes, {post.num_comments} comments")
    
    return reasons

