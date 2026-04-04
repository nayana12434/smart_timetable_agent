import streamlit as st
import datetime
import os
import pickle
import google.generativeai as genai
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def add_to_calendar(task, date, time):
    try:
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
        return True
    except Exception as e:
        st.error(f"Calendar sync failed: {e}")
        return False

# Gemini AI function
def ask_gemini(prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
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
        add_to_calendar(task, date, time)
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

