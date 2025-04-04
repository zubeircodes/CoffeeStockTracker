import os
import pickle
import json
import datetime
from pathlib import Path
from flask import session, current_app, redirect, url_for

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configuration for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_PATH = 'token.pickle'

# Google OAuth credentials from environment
CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')

def get_calendar_service():
    """
    Get an authorized Google Calendar service object.
    For web applications, this will check the session for credentials first.
    If not found or invalid, it returns None to trigger authentication flow.
    
    Returns:
        A Google Calendar API service object or None if authentication is needed.
    """
    # First check if we have credentials in the session (web flow)
    if 'credentials' in session:
        creds_dict = session['credentials']
        creds = Credentials(
            token=creds_dict['token'],
            refresh_token=creds_dict['refresh_token'],
            token_uri=creds_dict['token_uri'],
            client_id=creds_dict['client_id'],
            client_secret=creds_dict['client_secret'],
            scopes=creds_dict['scopes']
        )
        
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update session
            session['credentials'] = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            
        return build('calendar', 'v3', credentials=creds)
    
    # Try to load saved token from file as fallback
    elif os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
            
            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save back to file
                with open(TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)
                    
            # Also store in session for future use
            session['credentials'] = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
                
            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            current_app.logger.error(f"Error loading token: {str(e)}")
    
    # No valid credentials found
    return None

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