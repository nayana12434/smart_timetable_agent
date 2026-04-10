import streamlit as st
import os
from utils.scheduler import suggest_slots
from dotenv import load_dotenv
from cal.calender_service import add_event, get_upcoming_events
from database.db import init_db, add_task, get_all_tasks, delete_task, mark_completed
from utils.conflict_checker import check_conflict, find_free_slots
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

def parse_schedule_input(user_text):
    prompt = f"""
Extract task, date and time from this input:
"{user_text}"

Return ONLY in JSON format like:
{{
  "task": "...",
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS"
}}

If unclear, return:
{{
  "error": "Could not understand"
}}
"""

    response = ask_gemini(prompt)

    import json
    try:
        data = json.loads(response)
        return data
    except:
        return {"error": "Invalid AI response"}        

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
            st.warning("⚠️ Conflict detected!")

            suggestions = suggest_slots(date, time)

            if suggestions:
                st.info("Suggested slots (click to schedule):")

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

        # 👉 HANDLE FREE TIME QUERY
        if "free time" in user_input.lower():
            from datetime import date as dt_date

            today = dt_date.today()
            free = find_free_slots(today)

            if free:
                st.success(f"Available slots today: {', '.join(free)}")
            else:
                st.warning("No free slots today")

        else:
            # 👉 NORMAL AI RESPONSE
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

#UI for natural iput
st.subheader("🧠 Smart Scheduling (AI)")

nl_input = st.text_input(
    "Describe your task",
    placeholder="e.g. Study physics tomorrow at 5pm"
)

if st.button("Parse Schedule"):
    if nl_input:
        parsed = parse_schedule_input(nl_input)

        if "error" in parsed:
            st.error("⚠️ Could not understand input. Please be clearer.")
        else:
            st.session_state.parsed_task = parsed


#show parsed result + confirm            
def parse_schedule_input(user_text):
    from datetime import datetime, timedelta
    import json
    import re

    prompt = f"""
Extract task, date and time from this input:
"{user_text}"

Rules:
- Return ONLY valid JSON
- Date format: YYYY-MM-DD
- Time format: HH:MM:SS (24-hour)

Example:
{{
  "task": "study math",
  "date": "2026-04-11",
  "time": "21:00:00"
}}
"""

    response = ask_gemini(prompt)

    try:
        # 🔥 STEP 1: Extract JSON safely
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return {"error": "Could not extract structured data"}

        data = json.loads(json_match.group())

        # 🔥 STEP 2: Handle "tomorrow"
        if "tomorrow" in user_text.lower():
            tomorrow = datetime.now().date() + timedelta(days=1)
            data["date"] = str(tomorrow)

        # 🔥 STEP 3: Convert time to 24-hour format (if needed)
        try:
            # Case: "9 pm"
            time_obj = datetime.strptime(data["time"], "%I %p")
            data["time"] = time_obj.strftime("%H:%M:%S")
        except:
            try:
                # Case: already "21:00" or "21:00:00"
                time_obj = datetime.strptime(data["time"], "%H:%M")
                data["time"] = time_obj.strftime("%H:%M:%S")
            except:
                pass  # Leave as-is if already correct

        # 🔥 STEP 4: Validate fields
        if not all(k in data for k in ["task", "date", "time"]):
            return {"error": "Missing required fields"}

        return data

    except Exception as e:
        return {"error": f"Parsing failed: {e}"}