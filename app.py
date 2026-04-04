import streamlit as st
import datetime

# 🔥 Google Calendar imports
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------- GOOGLE CALENDAR SETUP ---------------- #

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)
    return service

def add_to_calendar(task, date, time):
    service = get_calendar_service()

    start_time = datetime.datetime.combine(date, time)
    end_time = start_time + datetime.timedelta(hours=1)

    event = {
        'summary': task,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
    }

    service.events().insert(calendarId='primary', body=event).execute()

# ---------------- UI START ---------------- #

st.title("Smart Timetable Assistant")

# Session storage
if "tasks" not in st.session_state:
    st.session_state.tasks = []

# ---------------- ADD TASK ---------------- #

st.subheader("Add Task")

task = st.text_input("Enter task name")
date = st.date_input("Select date")
time = st.time_input("Select time")

if st.button("Add Task"):
    st.session_state.tasks.append({
        "task": task,
        "date": date,
        "time": time
    })

    # 🔥 Google Calendar sync
    add_to_calendar(task, date, time)

    st.success("Task added + synced to Google Calendar ✅")

# ---------------- DISPLAY TASKS ---------------- #

st.subheader("Your Tasks")

sorted_tasks = sorted(
    st.session_state.tasks,
    key=lambda x: (x["date"], x["time"])
)

for i, t in enumerate(sorted_tasks):
    col1, col2 = st.columns([4, 1])

    with col1:
        st.write(f"📌 {t['task']} on {t['date']} at {t['time']}")

    with col2:
        if st.button("❌", key=f"delete_{i}"):
            st.session_state.tasks.remove(t)
            st.rerun()

# ---------------- SMART SUGGESTIONS ---------------- #

st.subheader("Smart Suggestions 🧠")

if st.session_state.tasks:
    next_task = sorted_tasks[0]

    st.info(
        f"👉 Next task: {next_task['task']} at {next_task['time']} on {next_task['date']}"
    )

    # Simple AI logic
    if "study" in next_task["task"].lower():
        st.success("💡 Suggestion: Focus mode ON. Avoid distractions.")
    elif "gym" in next_task["task"].lower():
        st.success("💡 Suggestion: Stay hydrated and warm up properly.")
    else:
        st.success("💡 Suggestion: Stay consistent and complete your task!")
else:
    st.warning("No tasks added yet!")

# ---------------- AI STUDY PLANNER ---------------- #

st.subheader("AI Study Planner 📅")

study_hours = st.slider("How many hours can you study today?", 1, 12, 4)

subjects = st.text_input(
    "Enter subjects (comma separated)",
    "Math, Physics, Chemistry"
)

if st.button("Generate Plan"):
    subject_list = [s.strip() for s in subjects.split(",")]

    total_subjects = len(subject_list)
    time_per_subject = study_hours / total_subjects

    st.write("### Your AI Generated Plan:")

    for subject in subject_list:
        st.write(f"🧠 {subject} → {round(time_per_subject,1)} hrs focus session")