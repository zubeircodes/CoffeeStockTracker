from datetime import datetime, timedelta
import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user

from app import db
from models import Staff, Shift
from forms import StaffForm, ShiftForm
from calendar_service import get_calendar_service, create_event, update_event, delete_event, get_events

staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/staff')
@login_required
def staff_list():
    """Display list of staff members"""
    staff_members = Staff.query.all()
    return render_template('staff/staff_list.html', staff=staff_members, title='Staff Directory')

@staff_bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
def create_staff():
    """Add a new staff member"""
    form = StaffForm()
    
    if form.validate_on_submit():
        # Split name into first and last name
        name_parts = form.name.data.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        staff = Staff(
            first_name=first_name,
            last_name=last_name,
            phone=form.phone.data,
            position=form.position.data,
            is_active=form.status.data == 'active',
            color="#" + ''.join([format(x, '02x') for x in [
                random.randint(100, 200), 
                random.randint(100, 200), 
                random.randint(100, 200)
            ]])  # Generate a random color
        )
        
        db.session.add(staff)
        db.session.commit()
        
        flash(f'Staff member {staff.name} has been added.', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/staff_form.html', form=form, title='Add Staff Member')

@staff_bp.route('/staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    """Edit an existing staff member"""
    staff = Staff.query.get_or_404(id)
    # Set the form's initial values
    form = StaffForm()
    if request.method == 'GET':
        form.name.data = staff.name
        form.phone.data = staff.phone
        form.position.data = staff.position
        form.status.data = 'active' if staff.is_active else 'inactive'
    
    if form.validate_on_submit():
        # Split name into first and last name
        name_parts = form.name.data.split(' ', 1)
        staff.first_name = name_parts[0]
        staff.last_name = name_parts[1] if len(name_parts) > 1 else ""
        staff.phone = form.phone.data
        staff.position = form.position.data
        staff.is_active = form.status.data == 'active'
        
        db.session.commit()
        
        flash(f'Staff member {staff.name} has been updated.', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/staff_form.html', form=form, staff=staff, title='Edit Staff Member')

@staff_bp.route('/staff/<int:id>/delete', methods=['POST'])
@login_required
def delete_staff(id):
    """Delete a staff member"""
    staff = Staff.query.get_or_404(id)
    
    # Check if staff member has shifts
    if staff.shifts:
        flash(f'Cannot delete {staff.name}. Please delete or reassign their shifts first.', 'danger')
        return redirect(url_for('staff.staff_list'))
    
    db.session.delete(staff)
    db.session.commit()
    
    flash(f'Staff member {staff.name} has been deleted.', 'success')
    return redirect(url_for('staff.staff_list'))

@staff_bp.route('/shifts')
@login_required
def shift_calendar():
    """Display shift calendar"""
    staff_members = Staff.query.filter_by(is_active=True).all()
    return render_template('staff/shift_calendar.html', staff=staff_members, title='Staff Schedule')
    
@staff_bp.route('/google-calendar')
@login_required
def google_calendar():
    """Display Google Calendar"""
    import os
    
    # Get staff members for the filter
    staff_members = Staff.query.filter_by(is_active=True).all()
    
    # Check if credentials exist in the environment
    if not os.environ.get('GOOGLE_OAUTH_CLIENT_ID') or not os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'):
        current_app.logger.error("Google OAuth credentials not configured in environment")
        error_message = "Google Calendar integration is not properly configured. Missing API credentials."
        return render_template(
            'staff/google_calendar.html',
            error=error_message,
            events=[],
            staff=staff_members,
            title='Google Calendar View'
        )
    
    try:
        # Get calendar service
        service = get_calendar_service()
        
        # If no service, we need authorization but don't redirect automatically
        if service is None:
            current_app.logger.debug("No Google Calendar service available - authentication required")
            error_message = "You need to connect your Google Calendar account to view and manage your calendar."
            return render_template(
                'staff/google_calendar.html',
                error=error_message,
                events=[],
                staff=staff_members,
                title='Google Calendar View'
            )
        
        # Get events for the next 30 days
        now = datetime.now()
        end_date = now + timedelta(days=30)
        events = get_events(service, time_min=now, time_max=end_date)
        
        # Get calendar ID (usually 'primary' or the user's email address)
        try:
            calendar_list = service.calendarList().list().execute()
            calendar_id = 'primary'  # Default to primary calendar
            
            # Find the primary calendar or use the first one if primary not found
            for calendar in calendar_list.get('items', []):
                if calendar.get('primary'):
                    calendar_id = calendar.get('id')
                    break
                    
            current_app.logger.debug(f"Using calendar ID: {calendar_id}")
        except Exception as cal_error:
            current_app.logger.error(f"Error getting calendar list: {str(cal_error)}")
            calendar_id = 'primary'  # Fall back to primary calendar
        
        return render_template(
            'staff/google_calendar.html',
            events=events,
            staff=staff_members,
            calendar_id=calendar_id,
            title='Google Calendar View'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error accessing Google Calendar: {str(e)}")
        error_message = f"Unable to connect to Google Calendar: {str(e)}"
        return render_template(
            'staff/google_calendar.html',
            error=error_message,
            events=[],
            staff=staff_members,
            title='Google Calendar View'
        )

@staff_bp.route('/shifts/add', methods=['GET', 'POST'])
@login_required
def create_shift():
    """Add a new shift"""
    form = ShiftForm()
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Create shift in database
        shift = Shift(
            staff_id=form.staff_id.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            title=f"{form.shift_type.data.capitalize()} Shift",
            notes=form.notes.data
        )
        
        db.session.add(shift)
        db.session.commit()
        
        # Try to create Google Calendar event
        try:
            # Get staff member
            staff = Staff.query.get(shift.staff_id)
            
            # Get calendar service
            service = get_calendar_service()
            
            # Check if we need to authenticate first
            if service is None:
                flash(f'Shift for {staff.name} has been added. Please authorize Google Calendar to sync shifts.', 'info')
                # Store the shift ID in session to sync after auth
                session['pending_shift_sync'] = shift.id
                return redirect(url_for('google_auth.authorize'))
            
            # Create event in Google Calendar
            event = create_event(
                service=service,
                start_time=shift.start_time,
                end_time=shift.end_time,
                summary=f"{staff.name} - {shift.shift_type.capitalize()} Shift",
                location=shift.location,
                description=shift.notes
            )
            
            flash(f'Shift for {staff.name} has been added and synced to calendar.', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Calendar sync error: {str(e)}")
            flash(f'Shift added to database, but calendar sync failed: {str(e)}', 'warning')
            
        return redirect(url_for('staff.shift_calendar'))
    
    return render_template('staff/shift_form.html', form=form, title='Add Shift')

@staff_bp.route('/shifts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_shift(id):
    """Edit an existing shift"""
    shift = Shift.query.get_or_404(id)
    
    # Set the form's initial values
    form = ShiftForm()
    if request.method == 'GET':
        form.staff_id.data = shift.staff_id
        form.start_time.data = shift.start_time
        form.end_time.data = shift.end_time
        form.shift_type.data = shift.shift_type
        form.notes.data = shift.notes
        
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Update shift in database
        old_staff_id = shift.staff_id
        
        shift.staff_id = form.staff_id.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.title = f"{form.shift_type.data.capitalize()} Shift"
        shift.notes = form.notes.data
        
        db.session.commit()
        
        # Try to update Google Calendar event
        try:
            # Get staff member
            staff = Staff.query.get(shift.staff_id)
            
            # Get calendar service
            service = get_calendar_service()
            
            # Update event in Google Calendar
            event = update_event(
                service=service,
                event_id=None,  # No event ID in new schema
                start_time=shift.start_time,
                end_time=shift.end_time,
                summary=f"{staff.name} - {shift.shift_type.capitalize()} Shift",
                location=shift.location,
                description=shift.notes
            )
            
            flash(f'Shift for {staff.name} has been updated and synced to calendar.', 'success')
        
        except Exception as e:
            flash(f'Shift updated in database, but calendar sync failed: {str(e)}', 'warning')
        
        return redirect(url_for('staff.shift_calendar'))
    
    return render_template('staff/shift_form.html', form=form, shift=shift, title='Edit Shift')

@staff_bp.route('/shifts/<int:id>/delete', methods=['POST'])
@login_required
def delete_shift(id):
    """Delete a shift"""
    shift = Shift.query.get_or_404(id)
    staff = Staff.query.get(shift.staff_id)
    
    # Try to delete Google Calendar event 
    try:
        service = get_calendar_service()
        # Note: We don't have event IDs in the new schema
        # This is a placeholder for future integration
        flash(f'Shift for {staff.name if staff else "Unknown"} has been deleted.', 'success')
    except Exception as e:
        flash(f'Could not connect to calendar service: {str(e)}', 'warning')
    
    db.session.delete(shift)
    db.session.commit()
    
    return redirect(url_for('staff.shift_calendar'))

@staff_bp.route('/api/shifts', methods=['GET'])
@login_required
def get_shifts_json():
    """Return shifts as JSON for calendar display"""
    start_date = request.args.get('start', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.args.get('end', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        # Default to current month if date parsing fails
        start_date = datetime.now().replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    
    # Query shifts within date range
    shifts = Shift.query.filter(
        Shift.start_time >= start_date,
        Shift.start_time <= end_date
    ).all()
    
    # Convert shifts to calendar events format
    events = []
    for shift in shifts:
        staff = Staff.query.get(shift.staff_id)
        
        # Set color based on staff's color or default color map by shift type
        if staff and staff.color:
            color = staff.color
        else:
            # Color map based on shift type
            color_map = {
                'opening': '#28a745',  # green
                'mid-day': '#17a2b8',  # blue
                'closing': '#6f42c1',  # purple
                'special': '#fd7e14'   # orange
            }
            color = color_map.get(shift.shift_type, '#6c757d')
        
        events.append({
            'id': shift.id,
            'title': f'{staff.name if staff else "Unknown"} - {shift.shift_type.capitalize()}',
            'start': shift.start_time.isoformat(),
            'end': shift.end_time.isoformat(),
            'color': color,
            'url': url_for('staff.edit_shift', id=shift.id),
            'staffId': shift.staff_id,
            'location': shift.location,
            'status': shift.status
        })
    
    return jsonify(events)

@staff_bp.route('/staff/<int:id>/shifts')
@login_required
def staff_shifts(id):
    """View shifts for a specific staff member"""
    staff = Staff.query.get_or_404(id)
    
    # Get upcoming shifts
    upcoming_shifts = Shift.query.filter_by(staff_id=id).filter(
        Shift.start_time >= datetime.now()
    ).order_by(Shift.start_time).all()
    
    # Get past shifts (last 30 days)
    past_shifts = Shift.query.filter_by(staff_id=id).filter(
        Shift.start_time < datetime.now(),
        Shift.start_time >= datetime.now() - timedelta(days=30)
    ).order_by(Shift.start_time.desc()).all()
    
    return render_template(
        'staff/staff_shifts.html',
        staff=staff,
        upcoming_shifts=upcoming_shifts,
        past_shifts=past_shifts,
        title=f'Shifts for {staff.name}'
    )