from database.academic_db import get_all_courses, get_upcoming_exams
from datetime import datetime, timedelta

def generate_study_plan(available_hours, subjects, priority_subject=None):
    if not subjects:
        return []

    plan = []
    hours_per_subject = available_hours / len(subjects)
    
    for subject in subjects:
        is_priority = subject == priority_subject
        allocated = hours_per_subject * 1.5 if is_priority else hours_per_subject
        plan.append({
            "subject": subject,
            "hours": round(allocated, 1),
            "sessions": max(1, int(allocated)),
            "break_after": 25 if allocated > 1 else 10
        })

    return plan

def generate_weekly_plan(courses, exam_dates=None):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    weekly = {}

    for i, day in enumerate(days):
        daily_subjects = []
        for j, course in enumerate(courses):
            if j % len(days) == i % len(days):
                daily_subjects.append(course)
        weekly[day] = daily_subjects

    return weekly

def days_until_exam(exam_date_str):
    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        delta = (exam_date - today).days
        return delta
    except:
        return None