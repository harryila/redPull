"""Configuration management for Reddit HireLab Listener."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class RedditConfig:
    """Reddit API configuration."""
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "hirelab-listener:v1 (by /u/yourusername)"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


@dataclass
class SlackConfig:
    """Slack integration configuration."""
    webhook_url: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)


@dataclass
class SheetsConfig:
    """Google Sheets integration configuration."""
    sheet_id: str = ""
    service_account_path: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.sheet_id and self.service_account_path)


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class AppConfig:
    """Application settings."""
    timezone: str = "America/Los_Angeles"
    intent_score_threshold: int = 55
    fetch_hours_lookback: int = 72
    posts_per_subreddit: int = 25
    dry_run: bool = False
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    
    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Default subreddits to monitor
DEFAULT_SUBREDDITS = [
    "resumes",
    "careerguidance",
    "jobs",
    "cscareerquestions",
    "EngineeringResumes",
    "internships",
    "layoffs",
    "recruitinghell",
]

# Subreddit weight multipliers for scoring
SUBREDDIT_WEIGHTS = {
    "resumes": 1.2,
    "EngineeringResumes": 1.2,
    "careerguidance": 1.1,
    "internships": 1.1,
    "jobs": 1.0,
    "cscareerquestions": 1.0,
    "layoffs": 1.0,
    "recruitinghell": 0.85,
}

# Keywords for matching (case-insensitive)
POSITIVE_KEYWORDS = [
    "resume",
    "cv",
    "ats",
    "no interviews",
    "rejected",
    "ghosted",
    "recruiter",
    "application",
    "cover letter",
    "screening",
    "parse",
    "job search",
    "internship",
    "entry level",
    "job hunting",
    "applying",
    "applications",
    "hiring manager",
    "tailoring",
    "customize",
    "keywords",
]

# High-intent phrases (bonus points)
HIGH_INTENT_PHRASES = [
    "no interviews",
    "ats",
    "rejected",
    "not getting callbacks",
    "not hearing back",
    "resume review",
    "resume help",
    "what tool",
    "any tool",
    "resume parser",
    "keyword optimization",
    "tailor my resume",
]

# Negative keywords (penalize)
NEGATIVE_KEYWORDS = [
    "survey",
    "research study",
    "giveaway",
    "promo",
    "discord",
    "my product",
    "affiliate",
    "spam",
    "promotion",
    "advertisement",
    "selling",
]

# Phrases that allow HireLab mention
MENTION_ALLOWED_PHRASES = [
    "ats",
    "resume parser",
    "keyword optimization",
    "formatting",
    "tailoring",
    "job application track",
    "what tool",
    "any tool",
    "recommend a tool",
    "tool recommendation",
    "software",
    "app for",
    "application for",
]


def load_config() -> tuple[RedditConfig, SlackConfig, SheetsConfig, OpenAIConfig, AppConfig]:
    """Load all configuration from environment variables."""
    reddit = RedditConfig(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        user_agent=os.getenv("REDDIT_USER_AGENT", "hirelab-listener:v1 (by /u/yourusername)"),
    )
    
    slack = SlackConfig(
        webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
    )
    
    sheets = SheetsConfig(
        sheet_id=os.getenv("GOOGLE_SHEETS_ID", ""),
        service_account_path=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", ""),
    )
    
    openai = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    
    app = AppConfig(
        timezone=os.getenv("TIMEZONE", "America/Los_Angeles"),
        intent_score_threshold=int(os.getenv("INTENT_SCORE_THRESHOLD", "55")),
        fetch_hours_lookback=int(os.getenv("FETCH_HOURS_LOOKBACK", "72")),
        posts_per_subreddit=int(os.getenv("POSTS_PER_SUBREDDIT", "25")),
        dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
    )
    
    return reddit, slack, sheets, openai, app

