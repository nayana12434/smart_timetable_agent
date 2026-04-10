from database.db import get_all_tasks
from datetime import datetime, timedelta

def check_conflict(new_date, new_time, duration_minutes=60):
    tasks = get_all_tasks()

    new_start = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M:%S")
    new_end = new_start + timedelta(minutes=duration_minutes)

    conflicts = []

    for t in tasks:
        existing_start = datetime.strptime(f"{t[2]} {t[3]}", "%Y-%m-%d %H:%M:%S")
        existing_end = existing_start + timedelta(hours=1)

        # Overlap check
        if (new_start < existing_end and new_end > existing_start):
            conflicts.append(t[1])

    return conflicts


def find_free_slots(date):
    tasks = get_all_tasks()

    busy_times = [
        t[3] for t in tasks if str(t[2]) == str(date)
    ]

    all_slots = [
        "08:00:00", "09:00:00", "10:00:00", "11:00:00",
        "12:00:00", "13:00:00", "14:00:00", "15:00:00",
        "16:00:00", "17:00:00", "18:00:00", "19:00:00",
        "20:00:00", "21:00:00"
    ]

    free_slots = [s for s in all_slots if s not in busy_times]
    return sorted(free_slots)