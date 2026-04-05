from database.db import get_all_tasks

def check_conflict(new_date, new_time):
    tasks = get_all_tasks()
    conflicts = []
    for t in tasks:
        task_id, task_name, task_date, task_time, completed = t
        if str(task_date) == str(new_date) and str(task_time) == str(new_time):
            conflicts.append(task_name)
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
    return free_slots