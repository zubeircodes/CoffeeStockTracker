import os
import pickle
import json
import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Configuration for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'

# Check if credentials file exists, if not create it from environment variables
if not os.path.exists(CREDENTIALS_PATH):
    # Get credentials from environment variables
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    project_id = os.environ.get('GOOGLE_PROJECT_ID')
    
    if client_id and client_secret and project_id:
        # Create credentials JSON
        credentials_data = {
            "installed": {
                "client_id": client_id,
                "project_id": project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
            }
        }
        
        # Write credentials to file
        with open(CREDENTIALS_PATH, 'w') as f:
            json.dump(credentials_data, f)

def get_calendar_service():
    """
    Get an authorized Google Calendar service object.
    If there are no valid credentials available, this will trigger the OAuth flow.
    
    Returns:
        A Google Calendar API service object.
    """
    creds = None
    
    # Try to load saved token
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are not valid, refresh or request new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Need to run OAuth flow
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"No credentials found at {CREDENTIALS_PATH}. Please set up OAuth credentials."
                )
            
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_PATH,
                scopes=SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f'Please go to this URL: {auth_url}')
            
            code = input('Enter the authorization code: ')
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save the credentials for the next run
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def create_event(service, start_time, end_time, summary, location=None, description=None, attendees=None, timezone='UTC'):
    """
    Create a calendar event.
    
    Args:
        service: The Google Calendar API service object.
        start_time: Event start time (datetime object).
        end_time: Event end time (datetime object).
        summary: Event title/summary.
        location: Event location (optional).
        description: Event description (optional).
        attendees: List of attendee email addresses (optional).
        timezone: Timezone for the event (default: UTC).
        
    Returns:
        The created event object.
    """
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        },
    }
    
    if location:
        event['location'] = location
    
    if description:
        event['description'] = description
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    return service.events().insert(calendarId='primary', body=event).execute()

def update_event(service, event_id, start_time=None, end_time=None, summary=None, 
                 location=None, description=None, attendees=None, timezone='UTC'):
    """
    Update an existing calendar event.
    
    Args:
        service: The Google Calendar API service object.
        event_id: The ID of the event to update.
        start_time: New event start time (datetime object), if changed.
        end_time: New event end time (datetime object), if changed.
        summary: New event title/summary, if changed.
        location: New event location, if changed.
        description: New event description, if changed.
        attendees: New list of attendee email addresses, if changed.
        timezone: Timezone for the event (default: UTC).
        
    Returns:
        The updated event object.
    """
    # First, get the existing event
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    # Update the fields that are provided
    if summary:
        event['summary'] = summary
    
    if start_time:
        event['start'] = {
            'dateTime': start_time.isoformat(),
            'timeZone': timezone,
        }
    
    if end_time:
        event['end'] = {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        }
    
    if location:
        event['location'] = location
    
    if description:
        event['description'] = description
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    return service.events().update(calendarId='primary', eventId=event_id, body=event).execute()

def delete_event(service, event_id):
    """
    Delete a calendar event.
    
    Args:
        service: The Google Calendar API service object.
        event_id: The ID of the event to delete.
        
    Returns:
        None
    """
    service.events().delete(calendarId='primary', eventId=event_id).execute()

def get_events(service, time_min=None, time_max=None, max_results=100, timezone='UTC'):
    """
    Get a list of upcoming events from the calendar.
    
    Args:
        service: The Google Calendar API service object.
        time_min: Start time for fetching events (datetime object).
        time_max: End time for fetching events (datetime object).
        max_results: Maximum number of events to return.
        timezone: Timezone for the query (default: UTC).
        
    Returns:
        List of events.
    """
    if not time_min:
        time_min = datetime.datetime.utcnow()
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min.isoformat() + 'Z',  # 'Z' indicates UTC time
        timeMax=time_max.isoformat() + 'Z' if time_max else None,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return events_result.get('items', [])