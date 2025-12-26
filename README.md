# 🎯 RedPull - Reddit Listening & Drafting System for HireLab

A production-ready system that monitors Reddit for high-intent posts about resumes, jobs, and recruiting, then generates thoughtful, non-promotional reply drafts for HireLab marketing.

> ⚠️ **Important**: This system is for **discovery and drafting only**. It does NOT automatically post to Reddit. All replies must be posted manually to comply with Reddit's ToS and community guidelines.

## Features

- 📡 **Smart Monitoring**: Tracks 8 high-value subreddits for resume/job-related discussions
- 🎯 **Intent Scoring**: Prioritizes posts most likely to benefit from engagement (0-100 score)
- 🔄 **Deduplication**: Prevents duplicate processing of cross-posts and reposts
- ✍️ **Draft Generation**: Creates human-sounding reply drafts (LLM-powered or template-based)
- 📊 **Multiple Outputs**: Slack notifications, Google Sheets tracking, or CSV export
- 🛡️ **Safe by Design**: No auto-posting, mention controls, and tone-appropriate drafts

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/harryila/redPull.git
cd redPull

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment

Copy `env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

#### Reddit API (Required for live mode)

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" as the app type
4. Set redirect URI to `http://localhost:8080`
5. Copy the client ID (under the app name) and secret

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=hirelab-listener:v1 (by /u/yourusername)
```

#### Slack (Optional)

1. Go to https://api.slack.com/apps
2. Create a new app → From scratch
3. Enable Incoming Webhooks
4. Add a webhook to your workspace
5. Copy the webhook URL

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

#### Google Sheets (Optional)

1. Go to https://console.cloud.google.com
2. Create a service account
3. Enable the Google Sheets API
4. Download the JSON key file
5. Share your Google Sheet with the service account email

```env
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/path/to/service-account.json
```

#### OpenAI (Optional)

Without OpenAI, the system uses high-quality template drafts.

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 3. Run

```bash
# Fetch posts and generate digest
hirelab fetch
hirelab digest

# Or run the combined script
python scripts/run_fetch_and_notify.py
```

## Usage

### CLI Commands

```bash
# Fetch new posts from Reddit
hirelab fetch
hirelab fetch --subreddits resumes --subreddits cscareerquestions

# Generate and send digest of high-intent posts
hirelab digest
hirelab digest --min-score 60 --limit 10

# List posts in database
hirelab list
hirelab list --status NEW --status QUEUED --min-score 55

# Show specific post details
hirelab show <reddit_id>

# Mark posts as replied/skipped
hirelab mark-replied <reddit_id> --notes "Posted reply on 2024-01-15"
hirelab mark-skipped <reddit_id> --notes "Off topic"

# Regenerate drafts for a post
hirelab regenerate <reddit_id>

# View database statistics
hirelab stats
```

### Scheduling with Cron

For automated monitoring, set up cron jobs:

```bash
# Open crontab
crontab -e

# Fetch and notify every 30 minutes
*/30 * * * * cd /path/to/redPull && /path/to/venv/bin/python scripts/run_fetch_and_notify.py >> /var/log/hirelab.log 2>&1

# Daily digest at 9am
0 9 * * * cd /path/to/redPull && /path/to/venv/bin/python scripts/run_daily_digest.py >> /var/log/hirelab-digest.log 2>&1
```

## How It Works

### Subreddits Monitored

| Subreddit | Weight | Notes |
|-----------|--------|-------|
| r/resumes | 1.2x | Primary target |
| r/EngineeringResumes | 1.2x | Technical resumes |
| r/careerguidance | 1.1x | Career advice |
| r/internships | 1.1x | Entry-level |
| r/jobs | 1.0x | General jobs |
| r/cscareerquestions | 1.0x | Tech careers |
| r/layoffs | 1.0x | Job seekers in transition |
| r/recruitinghell | 0.85x | Cautious engagement |

### Intent Scoring (0-100)

Posts are scored based on:
- **Keyword matches**: +5 each (capped at +40)
- **High-intent phrases**: +10 each for "ATS", "no interviews", etc. (capped at +30)
- **Subreddit weight**: Multiplier based on relevance
- **Engagement**: Bonus for upvotes and comments (capped at +15)
- **Negative keywords**: -15 for spam indicators (capped at -30)

Default threshold: **55** (configurable via `INTENT_SCORE_THRESHOLD`)

### Draft Generation Guidelines

All drafts follow these principles:
- ✅ Helpful first, not promotional
- ✅ Empathetic and authentic tone
- ✅ Concrete, actionable advice
- ✅ HireLab mentioned at most once, only when natural
- ❌ No links unless user explicitly asked
- ❌ No CTAs ("sign up", "check out", "try now")
- ❌ No startup/product language

**Draft A**: Always no product mention  
**Draft B**: Soft mention only if context allows (tool recommendations, ATS discussion)

## Project Structure

```
redPull/
├── src/
│   ├── config.py           # Configuration management
│   ├── reddit_client.py    # PRAW wrapper
│   ├── fetch.py            # Fetch orchestration
│   ├── scoring.py          # Intent scoring
│   ├── dedupe.py           # Deduplication
│   ├── cli.py              # Click CLI
│   ├── drafts/
│   │   ├── generator.py    # LLM/template draft generation
│   │   └── prompt_templates.py
│   ├── outputs/
│   │   ├── slack.py        # Slack webhook
│   │   ├── sheets.py       # Google Sheets/CSV
│   │   └── console.py      # Rich console output
│   └── store/
│       ├── db.py           # SQLite database
│       └── models.py       # Data models
├── scripts/
│   ├── run_fetch_and_notify.py
│   └── run_daily_digest.py
├── data/
│   ├── hirelab_reddit.sqlite
│   └── queue.csv
├── env.example
├── pyproject.toml
└── README.md
```

## Database Schema

### Posts Table
- `reddit_id` (unique)
- `subreddit`, `title`, `selftext`, `url`, `author`
- `created_utc`, `score`, `num_comments`
- `matched_keywords` (JSON)
- `intent_score`
- `status`: NEW → QUEUED → SENT → REPLIED/SKIPPED
- `content_hash` (for deduplication)
- `draft_a`, `draft_b`

### Actions Table
- Tracks all actions taken on posts
- Types: DRAFTED, SENT_TO_SLACK, WRITTEN_TO_SHEETS, MARK_REPLIED, MARK_SKIPPED

## Safety & Compliance

⚠️ **Reddit ToS Compliance**:
- This tool does NOT auto-post to Reddit
- All engagement must be manual and genuine
- Follow subreddit rules for self-promotion
- Use drafts as starting points, personalize before posting

🛡️ **Best Practices**:
- Engage authentically, not mechanically
- Prioritize helping over promoting
- Only mention HireLab when genuinely relevant
- Space out your engagements
- Build karma through genuine participation

## Troubleshooting

### "Reddit API not configured"
Set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in your `.env` file.

### "Rate limited"
PRAW handles rate limiting automatically, but if you see issues:
- Reduce `POSTS_PER_SUBREDDIT` in config
- Increase time between fetch runs

### No posts appearing
- Check `FETCH_HOURS_LOOKBACK` (default: 72 hours)
- Lower `INTENT_SCORE_THRESHOLD` temporarily
- Run `hirelab list --status NEW --min-score 0` to see all posts

### LLM drafts not generating
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota/billing
- System falls back to templates automatically

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details.

