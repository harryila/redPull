"""Draft generation using LLM or templates."""

import re
from typing import Optional

from ..config import OpenAIConfig
from ..store.models import Post
from .prompt_templates import (
    SYSTEM_PROMPT,
    get_user_prompt,
    TEMPLATE_DRAFTS,
    select_template,
)


def generate_drafts(
    post: Post,
    openai_config: OpenAIConfig,
) -> tuple[str, str]:
    """
    Generate draft replies for a Reddit post.
    
    Args:
        post: The Reddit post to generate drafts for
        openai_config: OpenAI API configuration
        
    Returns:
        Tuple of (draft_a, draft_b)
    """
    if openai_config.is_configured:
        return _generate_with_llm(post, openai_config)
    else:
        return _generate_with_templates(post)


def _generate_with_llm(
    post: Post,
    openai_config: OpenAIConfig,
) -> tuple[str, str]:
    """Generate drafts using OpenAI API."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=openai_config.api_key)
        
        user_prompt = get_user_prompt(
            subreddit=post.subreddit,
            title=post.title,
            selftext=post.selftext,
            mention_allowed=post.mention_allowed,
        )
        
        response = client.chat.completions.create(
            model=openai_config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        
        content = response.choices[0].message.content
        
        # Parse the response
        draft_a, draft_b = _parse_llm_response(content)
        
        if draft_a and draft_b:
            return draft_a, draft_b
        else:
            # Fallback to templates if parsing fails
            print("[WARN] Failed to parse LLM response, falling back to templates")
            return _generate_with_templates(post)
            
    except Exception as e:
        print(f"[WARN] LLM generation failed: {e}, falling back to templates")
        return _generate_with_templates(post)


def _parse_llm_response(content: str) -> tuple[Optional[str], Optional[str]]:
    """Parse the LLM response to extract draft A and B."""
    draft_a = None
    draft_b = None
    
    # Try to extract Draft A
    match_a = re.search(
        r'---DRAFT_A---\s*(.*?)\s*---END_DRAFT_A---',
        content,
        re.DOTALL
    )
    if match_a:
        draft_a = match_a.group(1).strip()
    
    # Try to extract Draft B
    match_b = re.search(
        r'---DRAFT_B---\s*(.*?)\s*---END_DRAFT_B---',
        content,
        re.DOTALL
    )
    if match_b:
        draft_b = match_b.group(1).strip()
    
    # If structured parsing failed, try simpler approach
    if not draft_a or not draft_b:
        parts = content.split("Draft B", 1)
        if len(parts) == 2:
            draft_a = parts[0].replace("Draft A", "").replace("---", "").strip()
            draft_a = re.sub(r'^[:\s]+', '', draft_a).strip()
            draft_b = parts[1].replace("---", "").strip()
            draft_b = re.sub(r'^[:\s]+', '', draft_b).strip()
    
    return draft_a, draft_b


def _generate_with_templates(post: Post) -> tuple[str, str]:
    """Generate drafts using predefined templates."""
    template_key = select_template(post.title, post.selftext)
    templates = TEMPLATE_DRAFTS[template_key]
    
    # If mention not allowed, use draft_a for both
    if not post.mention_allowed:
        return templates["draft_a"], templates["draft_a"]
    
    return templates["draft_a"], templates["draft_b"]


def validate_draft(draft: str) -> list[str]:
    """
    Validate a draft for compliance with our guidelines.
    
    Returns a list of warnings if any issues are found.
    """
    warnings = []
    draft_lower = draft.lower()
    
    # Check for forbidden phrases
    forbidden = [
        "sign up",
        "check out our",
        "my startup",
        "we're launching",
        "game changer",
        "revolutionize",
        "click here",
        "limited time",
        "discount",
        "promo code",
    ]
    
    for phrase in forbidden:
        if phrase in draft_lower:
            warnings.append(f"Contains forbidden phrase: '{phrase}'")
    
    # Check for links (unless explicitly allowed)
    if re.search(r'https?://', draft):
        warnings.append("Contains URL link")
    
    # Check for excessive HireLab mentions
    hirelab_count = draft_lower.count("hirelab")
    if hirelab_count > 1:
        warnings.append(f"Mentions HireLab {hirelab_count} times (should be max 1)")
    
    # Check for overly promotional tone
    promo_indicators = ["best tool", "amazing", "incredible", "must try", "you need to"]
    promo_count = sum(1 for indicator in promo_indicators if indicator in draft_lower)
    if promo_count >= 2:
        warnings.append("Draft may sound too promotional")
    
    return warnings

