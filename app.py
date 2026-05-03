from database.academic_db import (
    init_academic_db, add_course, get_all_courses, delete_course,
    add_class_schedule, get_schedule_by_day, get_all_classes, delete_class,
    add_exam, get_upcoming_exams, get_all_exams, delete_exam
)
import streamlit as st
import os
import re
from datetime import datetime, timedelta, date as dt_date
from dotenv import load_dotenv
from cal.calender_service import add_event, get_upcoming_events
from database.db import init_db, add_task, get_all_tasks, delete_task, mark_completed
from database.academic_db import (
    init_academic_db, add_course, get_all_courses,
    add_class_schedule, get_schedule_by_day,
    add_exam, get_upcoming_exams
)
from utils.conflict_checker import check_conflict, find_free_slots
from utils.scheduler import suggest_slots
from utils.study_planner import generate_study_plan, generate_weekly_plan, days_until_exam
from groq import Groq

load_dotenv()
init_db()
init_academic_db()

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
    if "tomorrow" in text:
        date = datetime.now().date() + timedelta(days=1)
        text = text.replace("tomorrow", "")
    elif "today" in text:
        date = datetime.now().date()
        text = text.replace("today", "")
    else:
        date = datetime.now().date()
    date_str = str(date)
    text = re.sub(r'\bat\b', '', text)
    text = re.sub(r'\bschedule\b|\badd\b|\bcreate\b', '', text)
    task = text.strip()
    if not task:
        return {"error": "Could not detect task"}
    return {"task": task, "date": date_str, "time": time_str}

# ---------------- APP CONFIG ---------------- #

st.set_page_config(
    page_title="Smart Timetable Assistant",
    page_icon="🗓️",
    layout="wide"
)

# ---------------- CUSTOM STYLING ---------------- #

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0f1117;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1f2e;
        border-right: 2px solid #2d3748;
    }
    
    /* Title styling */
    h1 {
        color: #667eea;
        text-align: center;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
    }
    
    /* Subheader styling */
    h2, h3 {
        color: #764ba2;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #1a1f2e;
        border: 1px solid #667eea;
        border-radius: 8px;
        color: white;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #1a1f2e;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Success/info/warning boxes */
    .stSuccess {
        border-radius: 10px;
    }
    
    .stInfo {
        border-radius: 10px;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1f2e;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #667eea;
    }
    
    /* Divider */
    hr {
        border-color: #2d3748;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #

with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/spiral-calendar.png", width=80)
    st.title("Navigation")

    page = st.radio("Go to", [
        "🏠 Home",
        "➕ Add Task",
        "📋 My Tasks",
        "🕐 Free Slots",
        "📅 Calendar Events",
        "🤖 AI Assistant",
        "📖 Study Planner",
        "🎓 Academic Manager"
    ])

    st.divider()
    st.write("**Quick Stats**")
    tasks = get_all_tasks()
    st.metric("Total Tasks", len(tasks))
    completed = sum(1 for t in tasks if t[4])
    st.metric("Completed", completed)
    st.metric("Pending", len(tasks) - completed)

    st.divider()
    st.caption("Smart Timetable Assistant v1.0")

# ---------------- MAIN TITLE ---------------- #

st.title("🗓️ Smart Timetable Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- HOME ---------------- #

if page == "🏠 Home":
    st.subheader("Welcome! 👋")
    st.write("Your AI-powered academic scheduling assistant.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📋 **{len(tasks)}** Total Tasks")
    with col2:
        st.success(f"✅ **{completed}** Completed")
    with col3:
        st.warning(f"⏳ **{len(tasks) - completed}** Pending")

    st.divider()
    st.write("### 📌 Today's Tasks")
    today = str(dt_date.today())
    today_tasks = [t for t in tasks if t[2] == today]
    if today_tasks:
        for t in today_tasks:
            st.write(f"📌 {t[1]} at {t[3]}")
    else:
        st.info("No tasks for today!")

    st.divider()
    st.write("### 📝 Upcoming Exams")
    exams = get_upcoming_exams()
    if exams:
        for e in exams[:3]:
            days_left = days_until_exam(e[2])
            if days_left is not None and days_left >= 0:
                st.warning(f"📝 {e[0]} — {e[1]} in {days_left} days")
    else:
        st.info("No upcoming exams!")

# ---------------- ADD TASK ---------------- #

elif page == "➕ Add Task":
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
                st.session_state.conflict_task = task
                st.session_state.conflict_date = date
                st.session_state.conflict_suggestions = suggest_slots(date, time)
                st.warning(f"⚠️ Conflict detected with: {', '.join(conflicts)}")
            else:
                add_task(task, date, time)
                add_event(task, date, time)
                st.success("Task added + synced to Google Calendar ✅")

    if "conflict_suggestions" in st.session_state:
        st.info("Suggested free slots:")
        for i, (s_date, s_time) in enumerate(st.session_state.conflict_suggestions):
            if st.button(f"{s_date} at {s_time}", key=f"suggest_{i}"):
                add_task(st.session_state.conflict_task, s_date, s_time)
                add_event(st.session_state.conflict_task, s_date, s_time)
                st.success(f"Scheduled at {s_date} {s_time} ✅")
                del st.session_state.conflict_suggestions
                del st.session_state.conflict_task
                st.rerun()

    st.divider()
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

# ---------------- MY TASKS ---------------- #

elif page == "📋 My Tasks":
    st.subheader("📋 Your Tasks")
    tasks = get_all_tasks()
    if tasks:
        for t in tasks:
            task_id, task_name, task_date, task_time, completed = t
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                if completed:
                    st.write(f"~~📌 {task_name}~~ on {task_date} at {task_time}")
                else:
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

elif page == "🕐 Free Slots":
    st.subheader("🕐 Find Free Slots")
    check_date = st.date_input("Check free slots for date")
    if st.button("Find Free Slots"):
        free = find_free_slots(check_date)
        if free:
            st.success(f"✅ Free slots: {', '.join(free)}")
        else:
            st.warning("No free slots on this date!")

# ---------------- CALENDAR EVENTS ---------------- #

elif page == "📅 Calendar Events":
    st.subheader("📅 Upcoming Calendar Events")
    if st.button("Fetch from Google Calendar"):
        events = get_upcoming_events()
        if events:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                st.write(f"📌 {event['summary']} — {start}")
        else:
            st.info("No upcoming events found!")

# ---------------- AI ASSISTANT ---------------- #

elif page == "🤖 AI Assistant":
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

# ---------------- STUDY PLANNER ---------------- #

elif page == "📖 Study Planner":
    st.subheader("📖 Smart Study Planner")

    tab_a, tab_b, tab_c = st.tabs(["📅 Daily Plan", "🗓️ Weekly Plan", "⏰ Exam Countdown"])

    with tab_a:
        st.write("### Generate Daily Study Plan")
        available_hours = st.slider("Available study hours today", 1, 12, 4)
        courses = get_all_courses()
        if courses:
            course_names = [c[1] for c in courses]
            selected_subjects = st.multiselect("Select subjects", course_names,
                default=course_names[:3] if len(course_names) >= 3 else course_names)
            priority = st.selectbox("Priority subject", ["None"] + course_names)
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
            st.warning("Please add courses in Academic Manager first!")

        st.divider()
        st.subheader("📅 AI Study Planner")
        study_hours = st.slider("How many hours can you study today?", 1, 12, 4,
            key="ai_hours")
        subjects = st.text_input("Enter subjects (comma separated)",
            "Math, Physics, Chemistry")
        if st.button("Generate AI Plan"):
            prompt = f"""Create a study schedule for a student with {study_hours} hours
available today for these subjects: {subjects}.
Include break times and study tips. Keep it concise."""
            with st.spinner("Generating plan..."):
                plan = ask_gemini(prompt)
            st.success(plan)

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
            st.info("No exams scheduled yet!")

# ---------------- ACADEMIC MANAGER ---------------- #
elif page == "🎓 Academic Manager":
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
                st.rerun()
            else:
                st.warning("Please enter a course name!")

        st.divider()
        st.write("### Your Courses")
        courses = get_all_courses()
        if courses:
            for c in courses:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📚 **{c[1]}** ({c[2]}) — {c[3]} credits — Prof. {c[4]}")
                with col2:
                    if st.button("🗑️", key=f"del_course_{c[0]}"):
                        delete_course(c[0])
                        st.success(f"{c[1]} deleted!")
                        st.rerun()
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
                st.rerun()

            st.divider()
            st.write("### All Classes")
            classes = get_all_classes()
            if classes:
                for cls in classes:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"📖 **{cls[1]}** ({cls[2]}) — {cls[3]} | {cls[4]} to {cls[5]} | Room: {cls[6]}")
                    with col2:
                        if st.button("🗑️", key=f"del_class_{cls[0]}"):
                            delete_class(cls[0])
                            st.success("Class deleted!")
                            st.rerun()
            else:
                st.info("No classes added yet!")
        else:
            st.warning("Please add courses first!")

    # ---------------- TAB 3: EXAMS ---------------- #
    with tab3:
        st.write("### Add Exam")
        courses = get_all_courses()
        if courses:
            course_options = {c[1]: c[0] for c in courses}
            selected_course = st.selectbox("Select Course",
                list(course_options.keys()), key="exam_course")
            exam_type = st.selectbox("Exam Type",
                ["Mid Term", "End Term", "Quiz", "Practical"])
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
                st.rerun()

            st.divider()
            st.write("### All Exams")
            exams = get_all_exams()
            if exams:
                for e in exams:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        days_left = days_until_exam(e[3])
                        if days_left is not None and days_left >= 0:
                            st.write(f"📝 **{e[1]}** — {e[2]} on {e[3]} at {e[4]} | Room: {e[5]} | {days_left} days left")
                        else:
                            st.write(f"📝 **{e[1]}** — {e[2]} on {e[3]} at {e[4]} | Room: {e[5]}")
                    with col2:
                        if st.button("🗑️", key=f"del_exam_{e[0]}"):
                            delete_exam(e[0])
                            st.success("Exam deleted!")
                            st.rerun()
            else:
                st.info("No exams scheduled yet!")
        else:
            st.warning("Please add courses first!")