from datetime import datetime, timedelta, timezone


def get_today_date():
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    print(f"today_date: Today is: {today}")
    return today
