"""Google Sheets output module."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import SheetsConfig
from ..store.models import Post


def write_to_sheets(
    posts: list[Post],
    sheets_config: SheetsConfig,
    fallback_csv_path: Optional[Path] = None,
) -> bool:
    """
    Write posts to Google Sheets or CSV fallback.
    
    Args:
        posts: List of posts to write
        sheets_config: Google Sheets configuration
        fallback_csv_path: Path for CSV fallback if Sheets not configured
        
    Returns:
        True if successful, False otherwise
    """
    if sheets_config.is_configured:
        return _write_to_gsheets(posts, sheets_config)
    elif fallback_csv_path:
        return _write_to_csv(posts, fallback_csv_path)
    else:
        print("[WARN] Neither Sheets nor CSV path configured, skipping")
        return False


def _write_to_gsheets(posts: list[Post], config: SheetsConfig) -> bool:
    """Write posts to Google Sheets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Setup credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            config.service_account_path,
            scopes=scopes,
        )
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.sheet_id)
        
        # Get or create the Queue worksheet
        try:
            worksheet = spreadsheet.worksheet("Queue")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Queue", rows=1000, cols=15)
            # Add headers
            headers = [
                "Date", "Reddit ID", "Subreddit", "Intent Score", "Title",
                "URL", "Author", "Status", "Draft A", "Draft B", "Notes"
            ]
            worksheet.append_row(headers)
        
        # Prepare rows
        rows = []
        for post in posts:
            rows.append([
                datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                post.reddit_id,
                post.subreddit,
                str(post.intent_score),
                post.title[:200],  # Truncate title
                post.url,
                post.author,
                post.status.value,
                post.draft_a[:500] if post.draft_a else "",  # Truncate drafts
                post.draft_b[:500] if post.draft_b else "",
                "",  # Notes column for manual input
            ])
        
        # Append rows
        if rows:
            worksheet.append_rows(rows)
        
        print(f"[INFO] Wrote {len(rows)} posts to Google Sheets")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to write to Google Sheets: {e}")
        return False


def _write_to_csv(posts: list[Post], csv_path: Path) -> bool:
    """Write posts to CSV file."""
    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists to determine if we need headers
        file_exists = csv_path.exists()
        
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write headers if new file
            if not file_exists:
                writer.writerow([
                    "Date", "Reddit ID", "Subreddit", "Intent Score", "Title",
                    "URL", "Author", "Status", "Draft A", "Draft B", "Notes"
                ])
            
            # Write posts
            for post in posts:
                writer.writerow([
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                    post.reddit_id,
                    post.subreddit,
                    post.intent_score,
                    post.title,
                    post.url,
                    post.author,
                    post.status.value,
                    post.draft_a,
                    post.draft_b,
                    "",  # Notes column
                ])
        
        print(f"[INFO] Wrote {len(posts)} posts to {csv_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to write to CSV: {e}")
        return False


def get_replied_ids_from_sheets(sheets_config: SheetsConfig) -> set[str]:
    """
    Get Reddit IDs that have been marked as REPLIED in Google Sheets.
    
    This allows syncing the local database with manual updates in the sheet.
    """
    if not sheets_config.is_configured:
        return set()
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ]
        creds = Credentials.from_service_account_file(
            sheets_config.service_account_path,
            scopes=scopes,
        )
        
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheets_config.sheet_id)
        worksheet = spreadsheet.worksheet("Queue")
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Find IDs with REPLIED status
        replied_ids = {
            r["Reddit ID"] for r in records
            if r.get("Status", "").upper() == "REPLIED"
        }
        
        return replied_ids
        
    except Exception as e:
        print(f"[WARN] Could not read from Google Sheets: {e}")
        return set()

