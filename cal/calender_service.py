import os
import pickle
import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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

def add_event(task, date, time):
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
        service.events().insert(
            calendarId='primary', body=event).execute()
        return True
    except Exception as e:
        return f"Error: {e}"

def get_upcoming_events(max_results=10):
    try:
        service = get_calendar_service()
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        return []

def delete_event(event_id):
    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        return True
    except Exception as e:
        return f"Error: {e}"
