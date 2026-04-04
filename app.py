import streamlit as st
import datetime
import os
from dotenv import load_dotenv
from cal.calender_service import add_event, get_upcoming_events
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

#Ask gemini
def ask_gemini(prompt):
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            client_options={"api_endpoint": "generativelanguage.googleapis.com"},
            transport="rest"
        )
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        st.write("DEBUG ERROR:", str(e))
        return f"AI error: {e}"

# ---------------- UI START ---------------- #

st.title("🗓️ Smart Timetable Assistant")

# Session storage
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- ADD TASK ---------------- #

st.subheader("Add Task")

task = st.text_input("Enter task name")
date = st.date_input("Select date")
time = st.time_input("Select time")

if st.button("Add Task"):
    if task:
        st.session_state.tasks.append({
            "task": task,
            "date": date,
            "time": time
        })
        add_event(task, date, time)
        st.success("Task added + synced to Google Calendar ✅")
    else:
        st.warning("Please enter a task name!")

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

# ---------------- UPCOMING EVENTS ---------------- #

st.subheader("📅 Upcoming Calendar Events")

if st.button("Fetch from Google Calendar"):
    events = get_upcoming_events()
    if events:
        for event in events:
            start = event['start'].get(
                'dateTime', event['start'].get('date'))
            st.write(f"📌 {event['summary']} — {start}")
    else:
        st.info("No upcoming events found!")

# ---------------- AI CHAT ASSISTANT ---------------- #

st.subheader("🤖 AI Scheduling Assistant")
st.write("Ask me anything about your schedule!")

user_input = st.text_input("Your question", 
    placeholder="e.g. How should I plan my study time today?")

if st.button("Ask AI"):
    if user_input:
        # Build context from tasks
        task_context = "\n".join([
            f"- {t['task']} on {t['date']} at {t['time']}"
            for t in st.session_state.tasks
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

# Show chat history
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

