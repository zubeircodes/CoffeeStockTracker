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

# Get Google OAuth credentials directly from environment
CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')

# Function to get the Replit domain for callback URL
def get_replit_domain():
    """Get the full Replit domain for the current environment.
    In development mode, use REPLIT_DEV_DOMAIN.
    """
    # First try REPLIT_DEV_DOMAIN which is more reliable for dev environments
    if 'REPLIT_DEV_DOMAIN' in os.environ:
        domain = os.environ['REPLIT_DEV_DOMAIN']
        current_app.logger.debug(f"Using Replit dev domain: {domain}")
        return domain
    # Fallback to constructing from SLUG and DOMAIN
    elif 'REPLIT_SLUG' in os.environ and 'REPLIT_DOMAIN' in os.environ:
        domain = os.environ.get('REPLIT_SLUG', '') + '.' + os.environ.get('REPLIT_DOMAIN', '')
        current_app.logger.debug(f"Using constructed Replit domain: {domain}")
        return domain
    # Last resort fallback
    else:
        # Get the host from the request
        domain = request.host
        current_app.logger.debug(f"Using request host: {domain}")
        return domain

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
        # Check if we have the necessary credentials
        if not CLIENT_ID or not CLIENT_SECRET:
            current_app.logger.error("Google OAuth credentials not found in environment variables")
            flash('Google OAuth credentials not configured. Please contact the administrator.', 'danger')
            return redirect(url_for('staff.shift_calendar'))
        
        # Create client config dictionary directly from environment variables
        client_config = {
            "web": {
                "client_id": CLIENT_ID,
                "project_id": PROJECT_ID,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [
                    url_for('google_auth.callback', _external=True, _scheme='https')
                ]
            }
        }
        
        # Log domain and redirect URI for debugging
        redirect_uri = url_for('google_auth.callback', _external=True, _scheme='https')
        current_app.logger.debug(f"OAuth redirect URI: {redirect_uri}")
        
        # Create the flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
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
            
        # Check if we have the necessary credentials
        if not CLIENT_ID or not CLIENT_SECRET:
            current_app.logger.error("Google OAuth credentials not found in environment variables")
            flash('Google OAuth credentials not configured. Please contact the administrator.', 'danger')
            return redirect(url_for('staff.shift_calendar'))
        
        # Create client config dictionary directly from environment variables
        client_config = {
            "web": {
                "client_id": CLIENT_ID,
                "project_id": PROJECT_ID,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [
                    url_for('google_auth.callback', _external=True, _scheme='https')
                ]
            }
        }
        
        # Log callback URL for debugging
        redirect_uri = url_for('google_auth.callback', _external=True, _scheme='https')
        current_app.logger.debug(f"OAuth callback URI: {redirect_uri}")
        current_app.logger.debug(f"Authorization response URL: {request.url}")
        
        # Create the flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for credentials
        # Ensure the authorization response URL is https
        authorization_response = request.url
        if authorization_response.startswith('http:'):
            authorization_response = authorization_response.replace('http:', 'https:', 1)
            current_app.logger.debug(f"Converted authorization URL to https: {authorization_response}")
        
        flow.fetch_token(authorization_response=authorization_response)
        
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