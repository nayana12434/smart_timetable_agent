import streamlit as st
import datetime
import os
from dotenv import load_dotenv
from cal.calender_service import add_event, get_upcoming_events
from database.db import init_db, add_task, get_all_tasks, delete_task, mark_completed
from groq import Groq

load_dotenv()
init_db()

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

st.title("🗓️ Smart Timetable Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.subheader("Add Task")
task = st.text_input("Enter task name")
date = st.date_input("Select date")
time = st.time_input("Select time")

if st.button("Add Task"):
    if task:
        add_task(task, date, time)
        add_event(task, date, time)
        st.success("Task added + synced to Google Calendar ✅")
    else:
        st.warning("Please enter a task name!")

st.subheader("Your Tasks")
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

st.subheader("📅 Upcoming Calendar Events")
if st.button("Fetch from Google Calendar"):
    events = get_upcoming_events()
    if events:
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            st.write(f"📌 {event['summary']} — {start}")
    else:
        st.info("No upcoming events found!")

st.subheader("🤖 AI Scheduling Assistant")
st.write("Ask me anything about your schedule!")
user_input = st.text_input("Your question",
    placeholder="e.g. How should I plan my study time today?")

if st.button("Ask AI"):
    if user_input:
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

