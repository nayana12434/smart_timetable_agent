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
# ---------------- ACADEMIC SCHEDULE MANAGER ---------------- #

from database.academic_db import (
    init_academic_db, add_course, get_all_courses,
    add_class_schedule, get_schedule_by_day,
    add_exam, get_upcoming_exams
)

init_academic_db()

st.subheader("🎓 Academic Schedule Manager")

tab1, tab2, tab3 = st.tabs(["📚 Courses", "📅 Class Schedule", "📝 Exams"])

# ---------------- TAB 1: COURSES ---------------- #

with tab1:
    st.write("### Add Course")
    col1, col2 = st.columns(2)
    with col1:
        course_name = st.text_input("Course Name", placeholder="e.g. Data Structures")
        course_code = st.text_input("Course Code", placeholder="e.g. CS301")
    with col2:
        credits = st.number_input("Credits", min_value=1, max_value=6, value=3)
        professor = st.text_input("Professor", placeholder="e.g. Dr. Sharma")

    if st.button("Add Course"):
        if course_name:
            add_course(course_name, course_code, credits, professor)
            st.success(f"Course {course_name} added! ✅")
        else:
            st.warning("Please enter a course name!")

    st.write("### Your Courses")
    courses = get_all_courses()
    if courses:
        for c in courses:
            st.write(f"📚 **{c[1]}** ({c[2]}) — {c[3]} credits — Prof. {c[4]}")
    else:
        st.info("No courses added yet!")

# ---------------- TAB 2: CLASS SCHEDULE ---------------- #

with tab2:
    st.write("### Add Class")
    courses = get_all_courses()

    if courses:
        course_options = {c[1]: c[0] for c in courses}
        selected_course = st.selectbox("Select Course", list(course_options.keys()))
        class_type = st.selectbox("Class Type", ["Lecture", "Lab", "Tutorial"])
        day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday",
                                    "Thursday", "Friday", "Saturday"])
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time", key="class_start")
        with col2:
            end_time = st.time_input("End Time", key="class_end")
        room = st.text_input("Room", placeholder="e.g. Room 301")

        if st.button("Add Class"):
            add_class_schedule(
                course_options[selected_course],
                class_type, day,
                str(start_time), str(end_time), room
            )
            st.success("Class added! ✅")

        st.write("### View Schedule by Day")
        view_day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday",
                                                "Thursday", "Friday", "Saturday"],
                                key="view_day")
        if st.button("View Schedule"):
            schedule = get_schedule_by_day(view_day)
            if schedule:
                for s in schedule:
                    st.write(f"📖 **{s[0]}** ({s[1]}) — {s[2]} to {s[3]} | Room: {s[4]}")
            else:
                st.info(f"No classes on {view_day}!")
    else:
        st.warning("Please add courses first!")

# ---------------- TAB 3: EXAMS ---------------- #

with tab3:
    st.write("### Add Exam")
    courses = get_all_courses()

    if courses:
        course_options = {c[1]: c[0] for c in courses}
        selected_course = st.selectbox("Select Course", list(course_options.keys()),
                                        key="exam_course")
        exam_type = st.selectbox("Exam Type", ["Mid Term", "End Term", "Quiz", "Practical"])
        exam_date = st.date_input("Exam Date", key="exam_date")
        exam_time = st.time_input("Exam Time", key="exam_time")
        exam_room = st.text_input("Exam Room", placeholder="e.g. Hall A")

        if st.button("Add Exam"):
            add_exam(
                course_options[selected_course],
                exam_type, str(exam_date),
                str(exam_time), exam_room
            )
            st.success("Exam added! ✅")

        st.write("### Upcoming Exams")
        exams = get_upcoming_exams()
        if exams:
            for e in exams:
                st.write(f"📝 **{e[0]}** — {e[1]} on {e[2]} at {e[3]} | Room: {e[4]}")
        else:
            st.info("No exams scheduled yet!")
    else:
        st.warning("Please add courses first!")
        # ---------------- SMART STUDY PLANNER (A2) ---------------- #

from utils.study_planner import generate_study_plan, generate_weekly_plan, days_until_exam

st.subheader("📖 Smart Study Planner")

tab_a, tab_b, tab_c = st.tabs(["📅 Daily Plan", "🗓️ Weekly Plan", "⏰ Exam Countdown"])

# ---------------- DAILY PLAN ---------------- #

with tab_a:
    st.write("### Generate Daily Study Plan")
    
    available_hours = st.slider("Available study hours today", 1, 12, 4, key="daily_hours")
    
    courses = get_all_courses()
    if courses:
        course_names = [c[1] for c in courses]
        selected_subjects = st.multiselect("Select subjects to study", course_names, default=course_names[:3] if len(course_names) >= 3 else course_names)
        priority = st.selectbox("Priority subject (gets more time)", ["None"] + course_names)
        
        if st.button("Generate Daily Plan"):
            if selected_subjects:
                priority_sub = None if priority == "None" else priority
                plan = generate_study_plan(available_hours, selected_subjects, priority_sub)
                
                st.write("### 📋 Your Study Plan:")
                for p in plan:
                    st.write(f"📚 **{p['subject']}** → {p['hours']} hrs | Break after {p['break_after']} mins")
                
                total = sum(p['hours'] for p in plan)
                st.info(f"Total study time: {round(total, 1)} hours")
            else:
                st.warning("Please select at least one subject!")
    else:
        st.warning("Please add courses first in Academic Schedule Manager!")

# ---------------- WEEKLY PLAN ---------------- #

with tab_b:
    st.write("### Generate Weekly Study Plan")
    
    courses = get_all_courses()
    if courses:
        if st.button("Generate Weekly Plan"):
            course_names = [c[1] for c in courses]
            weekly = generate_weekly_plan(course_names)
            
            for day, subjects in weekly.items():
                if subjects:
                    st.write(f"**{day}:** {', '.join(subjects)}")
                else:
                    st.write(f"**{day}:** Rest day 😴")
    else:
        st.warning("Please add courses first!")

# ---------------- EXAM COUNTDOWN ---------------- #

with tab_c:
    st.write("### Exam Countdown")
    
    exams = get_upcoming_exams()
    if exams:
        for e in exams:
            days_left = days_until_exam(e[2])
            if days_left is not None:
                if days_left < 0:
                    st.error(f"❌ **{e[0]}** {e[1]} — Already passed!")
                elif days_left == 0:
                    st.error(f"🚨 **{e[0]}** {e[1]} — TODAY!")
                elif days_left <= 3:
                    st.warning(f"⚠️ **{e[0]}** {e[1]} — {days_left} days left!")
                else:
                    st.success(f"✅ **{e[0]}** {e[1]} — {days_left} days left")
    else:
        st.info("No exams scheduled yet! Add them in Academic Schedule Manager.")