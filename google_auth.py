import os
import json
import pickle
from datetime import datetime, timedelta

import requests
from flask import Blueprint, redirect, request, url_for, session, flash, current_app
from flask_login import login_required, current_user
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'

# Set up environment variables and secrets
def get_replit_domain():
    return os.environ.get('REPLIT_SLUG', '') + '.' + os.environ.get('REPLIT_DOMAIN', '')

# Create Blueprint
google_auth_bp = Blueprint('google_auth', __name__)

def credentials_to_dict(credentials):
    """Convert credentials to a dictionary for session storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_calendar_service_web():
    """Get an authorized Google Calendar service using web flow."""
    creds = None
    
    # Try to get credentials from session
    if 'credentials' in session:
        from google.oauth2.credentials import Credentials
        creds = Credentials(**session['credentials'])
    
    # If credentials are not valid, redirect to authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            session['credentials'] = credentials_to_dict(creds)
        else:
            # No valid credentials, return None to trigger auth flow
            return None
    
    # Return the calendar service
    return build('calendar', 'v3', credentials=creds)

@google_auth_bp.route('/google_auth/authorize')
@login_required
def authorize():
    """Start the OAuth 2.0 authorization flow."""
    try:
        # Get credentials from file or environment variables
        client_config = {}
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, 'r') as f:
                client_config = json.load(f)
        
        # Replace environment variables in redirect_uris
        if 'web' in client_config and 'redirect_uris' in client_config['web']:
            new_uris = []
            for uri in client_config['web']['redirect_uris']:
                if '$REPLIT_DOMAIN' in uri:
                    domain = get_replit_domain()
                    uri = uri.replace('$REPLIT_DOMAIN', domain)
                new_uris.append(uri)
            client_config['web']['redirect_uris'] = new_uris
        
        # Create the flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=url_for('google_auth.callback', _external=True, _scheme='https')
        )
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store the state for verification in the callback
        session['state'] = state
        
        # Redirect to Google's authorization page
        return redirect(authorization_url)
    
    except Exception as e:
        flash(f'Error starting authorization: {str(e)}', 'danger')
        current_app.logger.error(f"Google Auth Error: {str(e)}")
        return redirect(url_for('staff.shift_calendar'))

@google_auth_bp.route('/google_auth/callback')
@login_required
def callback():
    """Handle the OAuth 2.0 callback."""
    try:
        # Check state to prevent CSRF
        state = session.get('state', None)
        if state is None or state != request.args.get('state', None):
            flash('Authentication failed: Invalid state parameter', 'danger')
            return redirect(url_for('staff.shift_calendar'))
        
        # Get credentials from file or environment variables
        client_config = {}
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, 'r') as f:
                client_config = json.load(f)
        
        # Replace environment variables in redirect_uris
        if 'web' in client_config and 'redirect_uris' in client_config['web']:
            new_uris = []
            for uri in client_config['web']['redirect_uris']:
                if '$REPLIT_DOMAIN' in uri:
                    domain = get_replit_domain()
                    uri = uri.replace('$REPLIT_DOMAIN', domain)
                new_uris.append(uri)
            client_config['web']['redirect_uris'] = new_uris
        
        # Create the flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=url_for('google_auth.callback', _external=True, _scheme='https')
        )
        
        # Exchange authorization code for credentials
        flow.fetch_token(authorization_response=request.url)
        
        # Store credentials in session
        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)
        
        # Save credentials to file for offline access
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(credentials, token)
        
        flash('Successfully connected to Google Calendar!', 'success')
        return redirect(url_for('staff.google_calendar'))
    
    except Exception as e:
        flash(f'Error completing authorization: {str(e)}', 'danger')
        current_app.logger.error(f"Google Auth Error: {str(e)}")
        return redirect(url_for('staff.shift_calendar'))

@google_auth_bp.route('/google_auth/revoke')
@login_required
def revoke():
    """Revoke Google Calendar authorization."""
    if 'credentials' not in session:
        flash('No active Google Calendar connection to revoke.', 'warning')
        return redirect(url_for('staff.shift_calendar'))
    
    try:
        credentials = session['credentials']
        revoke_url = f'https://accounts.google.com/o/oauth2/revoke?token={credentials["token"]}'
        
        # Make the revocation request
        requests.get(revoke_url, 
                    headers={'content-type': 'application/x-www-form-urlencoded'})
        
        # Clear session and token file
        session.pop('credentials', None)
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
        
        flash('Google Calendar connection has been revoked.', 'success')
    except Exception as e:
        flash(f'Error revoking authorization: {str(e)}', 'warning')
    
    return redirect(url_for('staff.shift_calendar'))