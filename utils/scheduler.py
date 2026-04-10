from database.db import get_all_tasks
from datetime import datetime, timedelta

def suggest_slots(date, current_time):
    tasks = get_all_tasks()
    date_str = str(date)

    all_slots = [
        "08:00:00", "09:00:00", "10:00:00", "11:00:00",
        "12:00:00", "13:00:00", "14:00:00", "15:00:00",
        "16:00:00", "17:00:00", "18:00:00", "19:00:00",
        "20:00:00", "21:00:00"
    ]

    busy_slots = [
        str(t[3]) for t in tasks if str(t[2]) == date_str
    ]

    current_dt = datetime.combine(date, current_time)

    suggestions = []

    # ✅ Same day future slots
    for slot in all_slots:
        slot_time = datetime.strptime(slot, "%H:%M:%S").time()
        slot_dt = datetime.combine(date, slot_time)

        if slot_dt > current_dt and slot not in busy_slots:
            suggestions.append((date, slot))

    # ✅ Next day slots (first few)
    next_day = date + timedelta(days=1)
    next_day_str = str(next_day)

    next_day_busy = [
        str(t[3]) for t in tasks if str(t[2]) == next_day_str
    ]

    for slot in all_slots:
        if slot not in next_day_busy:
            suggestions.append((next_day, slot))

        if len(suggestions) >= 5:
            break

    return suggestions
