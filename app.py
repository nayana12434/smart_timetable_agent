import streamlit as st
import os
import json
import re
from datetime import datetime, timedelta, date as dt_date
from dotenv import load_dotenv
from cal.calender_service import add_event, get_upcoming_events
from database.db import init_db, add_task, get_all_tasks, delete_task, mark_completed
from utils.conflict_checker import check_conflict, find_free_slots
from utils.scheduler import suggest_slots
from groq import Groq

load_dotenv()
init_db()

# ---------------- AI FUNCTION ---------------- #

def ask_gemini(prompt):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI error: {e}"

# ---------------- NLP PARSER ---------------- #

def parse_schedule_input(user_text):
    text = user_text.lower()

    # STEP 1: EXTRACT TIME
    time_match = re.search(r'(\d{1,2})\s*(am|pm)', text)
    if not time_match:
        return {"error": "Could not detect time"}

    hour = int(time_match.group(1))
    period = time_match.group(2)
    if period == "pm" and hour != 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0
    time_str = f"{hour:02d}:00:00"
    text = text.replace(time_match.group(), "")

    # STEP 2: EXTRACT DATE
    if "tomorrow" in text:
        date = datetime.now().date() + timedelta(days=1)
        text = text.replace("tomorrow", "")
    elif "today" in text:
        date = datetime.now().date()
        text = text.replace("today", "")
    else:
        date = datetime.now().date()
    date_str = str(date)

    # STEP 3: CLEAN TASK
    text = re.sub(r'\bat\b', '', text)
    text = re.sub(r'\bschedule\b|\badd\b|\bcreate\b', '', text)
    task = text.strip()

    if not task:
        return {"error": "Could not detect task"}

    return {"task": task, "date": date_str, "time": time_str}

# ---------------- APP START ---------------- #

st.title("🗓️ Smart Timetable Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- ADD TASK ---------------- #

st.subheader("➕ Add Task")
task = st.text_input("Enter task name")
date = st.date_input("Select date")
time = st.time_input("Select time")

if st.button("Add Task"):
    if not task:
        st.warning("Please enter a task name!")
    else:
        conflicts = check_conflict(date, time)
        if conflicts:
            st.warning(f"⚠️ Conflict detected with: {', '.join(conflicts)}")
            suggestions = suggest_slots(date, time)
            if suggestions:
                st.info("Suggested free slots:")
                for i, (s_date, s_time) in enumerate(suggestions):
                    if st.button(f"{s_date} at {s_time}", key=f"suggest_{i}"):
                        add_task(task, s_date, s_time)
                        add_event(task, s_date, s_time)
                        st.success(f"Scheduled at {s_date} {s_time} ✅")
                        st.rerun()
            else:
                st.error("No available slots found!")
        else:
            add_task(task, date, time)
            add_event(task, date, time)
            st.success("Task added + synced to Google Calendar ✅")

# ---------------- DISPLAY TASKS ---------------- #

st.subheader("📋 Your Tasks")
tasks = get_all_tasks()
if tasks:
    for t in tasks:
        task_id, task_name, task_date, task_time, completed = t
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"📌 {task_name} on {task_date} at {task_time}")
        with col2:
            if st.button("✅", key=f"done_{task_id}"):
                mark_completed(task_id)
                st.rerun()
        with col3:
            if st.button("❌", key=f"del_{task_id}"):
                delete_task(task_id)
                st.rerun()
else:
    st.info("No tasks yet!")

# ---------------- FREE SLOTS ---------------- #

st.subheader("🕐 Find Free Slots")
check_date = st.date_input("Check free slots for date", key="free_slot_date")
if st.button("Find Free Slots"):
    free = find_free_slots(check_date)
    if free:
        st.success(f"✅ Free slots: {', '.join(free)}")
    else:
        st.warning("No free slots on this date!")

# ---------------- UPCOMING EVENTS ---------------- #

st.subheader("📅 Upcoming Calendar Events")
if st.button("Fetch from Google Calendar"):
    events = get_upcoming_events()
    if events:
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            st.write(f"📌 {event['summary']} — {start}")
    else:
        st.info("No upcoming events found!")

# ---------------- AI CHAT ---------------- #

st.subheader("🤖 AI Scheduling Assistant")
st.write("Ask me anything about your schedule!")
user_input = st.text_input("Your question",
    placeholder="e.g. How should I plan my study time today?")

if st.button("Ask AI"):
    if user_input:
        if "free time" in user_input.lower():
            today = dt_date.today()
            free = find_free_slots(today)
            if free:
                st.success(f"Available slots today: {', '.join(free)}")
            else:
                st.warning("No free slots today!")
        else:
            tasks = get_all_tasks()
            task_context = "\n".join([
                f"- {t[1]} on {t[2]} at {t[3]}"
                for t in tasks
            ]) or "No tasks yet"
            prompt = f"""You are a smart student scheduling assistant.
The student has these tasks:
{task_context}

Student asks: {user_input}

Give a helpful, concise scheduling suggestion."""
            with st.spinner("Thinking..."):
                response = ask_gemini(prompt)
            st.session_state.chat_history.append({
                "q": user_input,
                "a": response
            })

for chat in st.session_state.chat_history[-3:]:
    st.write(f"**You:** {chat['q']}")
    st.info(f"**AI:** {chat['a']}")

# ---------------- AI STUDY PLANNER ---------------- #

st.subheader("📅 AI Study Planner")
study_hours = st.slider("How many hours can you study today?", 1, 12, 4)
subjects = st.text_input("Enter subjects (comma separated)",
    "Math, Physics, Chemistry")

if st.button("Generate AI Plan"):
    prompt = f"""Create a study schedule for a student with {study_hours} hours
available today for these subjects: {subjects}.
Include break times and study tips. Keep it concise."""
    with st.spinner("Generating plan..."):
        plan = ask_gemini(prompt)
    st.success(plan)

# ---------------- SMART SCHEDULING ---------------- #

st.subheader("🧠 Smart Scheduling (NLP)")
nl_input = st.text_input("Describe your task",
    placeholder="e.g. Study physics tomorrow at 5pm")

if st.button("Parse Schedule"):
    if nl_input:
        parsed = parse_schedule_input(nl_input)
        if "error" in parsed:
            st.error("⚠️ Could not understand. Try: 'Study Math tomorrow at 3pm'")
        else:
            st.session_state.parsed_task = parsed

if "parsed_task" in st.session_state:
    parsed = st.session_state.parsed_task
    st.success(f"✅ Detected: **{parsed['task']}** on **{parsed['date']}** at **{parsed['time']}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm & Add"):
            add_task(parsed['task'], parsed['date'], parsed['time'])
            add_event(parsed['task'], parsed['date'], parsed['time'])
            st.success("Task added!")
            del st.session_state.parsed_task
            st.rerun()
    with col2:
        if st.button("❌ Cancel"):
            del st.session_state.parsed_task
            st.rerun()
