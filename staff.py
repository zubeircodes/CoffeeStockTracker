from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models import Staff, Shift
from forms import StaffForm, ShiftForm

# Blueprint for staff routes
staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/staff', methods=['GET'])
@login_required
def staff_list():
    """
    Display list of staff members
    """
    staff = Staff.query.order_by(Staff.first_name, Staff.last_name).all()
    return render_template('staff/staff_list.html', staff=staff, title='Staff Management')

@staff_bp.route('/staff/create', methods=['GET', 'POST'])
@login_required
def create_staff():
    """
    Create a new staff member
    """
    form = StaffForm()
    
    if form.validate_on_submit():
        # Generate default color based on position
        position_colors = {
            'barista': '#28a745',  # green
            'manager': '#007bff',  # blue
            'cashier': '#fd7e14',  # orange
            'cook': '#dc3545',     # red
            'server': '#6f42c1'    # purple
        }
        default_color = position_colors.get(form.position.data, '#6c757d')
        
        staff = Staff(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            position=form.position.data,
            role=form.role.data,
            hourly_rate=form.hourly_rate.data,
            hire_date=form.hire_date.data,
            is_active=form.is_active.data,
            color=form.color.data or default_color,
            user_id=current_user.id
        )
        db.session.add(staff)
        db.session.commit()
        flash('Staff member added successfully!', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/staff_form.html', form=form, title='Add Staff Member')

@staff_bp.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    """
    Edit a staff member
    """
    staff = Staff.query.get_or_404(id)
    form = StaffForm()
    
    if request.method == 'GET':
        form.first_name.data = staff.first_name
        form.last_name.data = staff.last_name
        form.phone.data = staff.phone
        form.position.data = staff.position if staff.position else 'barista'
        form.role.data = staff.role if staff.role else 'employee'
        form.hourly_rate.data = staff.hourly_rate
        form.hire_date.data = staff.hire_date
        form.is_active.data = staff.is_active
        form.color.data = staff.color
        form.id.data = staff.id
    
    if form.validate_on_submit():
        staff.first_name = form.first_name.data
        staff.last_name = form.last_name.data
        staff.phone = form.phone.data
        staff.position = form.position.data
        staff.role = form.role.data
        staff.hourly_rate = form.hourly_rate.data
        staff.hire_date = form.hire_date.data
        staff.is_active = form.is_active.data
        staff.color = form.color.data
        staff.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Staff details updated successfully!', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/staff_form.html', form=form, staff=staff, title='Edit Staff Member')

@staff_bp.route('/staff/delete/<int:id>', methods=['POST'])
@login_required
def delete_staff(id):
    """
    Delete a staff member
    """
    staff = Staff.query.get_or_404(id)
    
    # Check if staff has shifts
    if staff.shifts:
        flash('Cannot delete staff member with associated shifts. Remove the shifts first or make the staff inactive.', 'danger')
        return redirect(url_for('staff.staff_list'))
    
    db.session.delete(staff)
    db.session.commit()
    flash('Staff member deleted successfully!', 'success')
    return redirect(url_for('staff.staff_list'))

# Shift management routes
@staff_bp.route('/shifts', methods=['GET'])
@login_required
def shift_list():
    """
    Display list of all shifts
    """
    shifts = Shift.query.order_by(Shift.start_time.desc()).all()
    return render_template('staff/shift_list.html', shifts=shifts, title='Shift Management')

@staff_bp.route('/shifts/create', methods=['GET', 'POST'])
@login_required
def create_shift():
    """
    Create a new shift
    """
    form = ShiftForm()
    
    # Populate staff dropdown
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(is_active=True).order_by(Staff.first_name, Staff.last_name)]
    
    if form.validate_on_submit():
        # Validate date and time fields
        if not form.start_date.data or not form.start_time.data or not form.end_time.data:
            flash('Please fill in all date and time fields.', 'danger')
            return render_template('staff/shift_form.html', form=form, title='Add Shift')
            
        # Combine date and time fields
        start_datetime = datetime.combine(form.start_date.data, form.start_time.data)
        end_datetime = datetime.combine(form.start_date.data, form.end_time.data)
        
        # If end time is earlier than start time, it must be the next day
        if end_datetime <= start_datetime:
            end_datetime = end_datetime + timedelta(days=1)
        
        # Build recurring days string from checkbox fields
        recurring_days = []
        if form.is_recurring.data:
            if form.monday.data:
                recurring_days.append('Mon')
            if form.tuesday.data:
                recurring_days.append('Tue')
            if form.wednesday.data:
                recurring_days.append('Wed')
            if form.thursday.data:
                recurring_days.append('Thu')
            if form.friday.data:
                recurring_days.append('Fri')
            if form.saturday.data:
                recurring_days.append('Sat')
            if form.sunday.data:
                recurring_days.append('Sun')
        
        recurring_days_str = ','.join(recurring_days) if recurring_days else ''
        
        shift = Shift(
            staff_id=form.staff_id.data,
            title=form.title.data,
            start_time=start_datetime,
            end_time=end_datetime,
            is_recurring=form.is_recurring.data,
            recurring_days=recurring_days_str,
            notes=form.notes.data
        )
        db.session.add(shift)
        db.session.commit()
        flash('Shift added successfully!', 'success')
        return redirect(url_for('staff.shift_list'))
    
    return render_template('staff/shift_form.html', form=form, title='Add Shift')

@staff_bp.route('/shifts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_shift(id):
    """
    Edit a shift
    """
    shift = Shift.query.get_or_404(id)
    form = ShiftForm()
    
    # Populate staff dropdown
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(is_active=True).order_by(Staff.first_name, Staff.last_name)]
    
    if request.method == 'GET':
        form.staff_id.data = shift.staff_id
        form.title.data = shift.title
        
        # Split datetime into date and time components
        form.start_date.data = shift.start_time.date()
        form.start_time.data = shift.start_time.time()
        form.end_time.data = shift.end_time.time()
        
        # Set recurring fields
        form.is_recurring.data = shift.is_recurring
        
        # Set individual day checkboxes based on recurring_days string
        if shift.recurring_days:
            days = shift.recurring_days.split(',')
            form.monday.data = 'Mon' in days
            form.tuesday.data = 'Tue' in days
            form.wednesday.data = 'Wed' in days
            form.thursday.data = 'Thu' in days
            form.friday.data = 'Fri' in days
            form.saturday.data = 'Sat' in days
            form.sunday.data = 'Sun' in days
            
        form.notes.data = shift.notes
    
    if form.validate_on_submit():
        # Validate date and time fields
        if not form.start_date.data or not form.start_time.data or not form.end_time.data:
            flash('Please fill in all date and time fields.', 'danger')
            return render_template('staff/shift_form.html', form=form, shift=shift, title='Edit Shift')
            
        # Combine date and time fields
        start_datetime = datetime.combine(form.start_date.data, form.start_time.data)
        end_datetime = datetime.combine(form.start_date.data, form.end_time.data)
        
        # If end time is earlier than start time, it must be the next day
        if end_datetime <= start_datetime:
            end_datetime = end_datetime + timedelta(days=1)
        
        # Build recurring days string from checkbox fields
        recurring_days = []
        if form.is_recurring.data:
            if form.monday.data:
                recurring_days.append('Mon')
            if form.tuesday.data:
                recurring_days.append('Tue')
            if form.wednesday.data:
                recurring_days.append('Wed')
            if form.thursday.data:
                recurring_days.append('Thu')
            if form.friday.data:
                recurring_days.append('Fri')
            if form.saturday.data:
                recurring_days.append('Sat')
            if form.sunday.data:
                recurring_days.append('Sun')
        
        recurring_days_str = ','.join(recurring_days) if recurring_days else ''
        
        shift.staff_id = form.staff_id.data
        shift.title = form.title.data
        shift.start_time = start_datetime
        shift.end_time = end_datetime
        shift.is_recurring = form.is_recurring.data
        shift.recurring_days = recurring_days_str
        shift.notes = form.notes.data
        shift.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Shift updated successfully!', 'success')
        return redirect(url_for('staff.shift_list'))
    
    return render_template('staff/shift_form.html', form=form, shift=shift, title='Edit Shift')

@staff_bp.route('/shifts/delete/<int:id>', methods=['POST'])
@login_required
def delete_shift(id):
    """
    Delete a shift
    """
    shift = Shift.query.get_or_404(id)
    db.session.delete(shift)
    db.session.commit()
    flash('Shift deleted successfully!', 'success')
    return redirect(url_for('staff.shift_list'))

@staff_bp.route('/schedule', methods=['GET'])
@login_required
def schedule():
    """
    Display staff schedule calendar
    """
    staff_members = Staff.query.filter_by(is_active=True).order_by(Staff.first_name, Staff.last_name).all()
    return render_template('staff/schedule.html', staff=staff_members, title='Staff Schedule')

@staff_bp.route('/schedule/data', methods=['GET'])
@login_required
def schedule_data():
    """
    API endpoint for calendar events
    """
    # Get date range from request or use default (1 month)
    start_date = request.args.get('start', (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', (datetime.utcnow() + timedelta(days=31)).strftime('%Y-%m-%d'))
    
    # Query shifts within date range
    shifts = Shift.query.filter(
        Shift.start_time >= start_date,
        Shift.end_time <= end_date
    ).all()
    
    # Format for FullCalendar
    events = []
    staff_colors = {
        'barista': '#28a745',  # green
        'manager': '#007bff',  # blue
        'cashier': '#fd7e14',  # orange
        'cook': '#dc3545',     # red
        'server': '#6f42c1'    # purple
    }
    
    for shift in shifts:
        # Get staff position for color coding
        position = shift.staff.position if shift.staff else 'barista'
        # Use staff's custom color if available, otherwise use position color
        color = shift.staff.color if shift.staff and shift.staff.color else staff_colors.get(position, '#6c757d')
        
        # Use shift title if available, otherwise use staff name and position
        display_title = shift.title if shift.title else f"{shift.staff.name} ({shift.staff.position.capitalize() if shift.staff and shift.staff.position else 'Staff'})"
        
        events.append({
            'id': shift.id,
            'title': display_title,
            'start': shift.start_time.isoformat(),
            'end': shift.end_time.isoformat(),
            'color': color,
            'extendedProps': {
                'staffId': shift.staff_id,
                'staffName': shift.staff.name,
                'position': position,
                'notes': shift.notes,
                'isRecurring': shift.is_recurring,
                'recurringDays': shift.recurring_days,
                'duration': shift.duration
            }
        })
    
    return jsonify(events)