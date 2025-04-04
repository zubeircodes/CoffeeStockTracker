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
    staff = Staff.query.order_by(Staff.name).all()
    return render_template('staff/staff_list.html', staff=staff, title='Staff Management')

@staff_bp.route('/staff/create', methods=['GET', 'POST'])
@login_required
def create_staff():
    """
    Create a new staff member
    """
    form = StaffForm()
    
    if form.validate_on_submit():
        staff = Staff(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            position=form.position.data,
            hourly_rate=form.hourly_rate.data,
            hire_date=form.hire_date.data,
            status=form.status.data
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
        form.name.data = staff.name
        form.email.data = staff.email
        form.phone.data = staff.phone
        form.position.data = staff.position
        form.hourly_rate.data = staff.hourly_rate
        form.hire_date.data = staff.hire_date
        form.status.data = staff.status
        form.id.data = staff.id
    
    if form.validate_on_submit():
        staff.name = form.name.data
        staff.email = form.email.data
        staff.phone = form.phone.data
        staff.position = form.position.data
        staff.hourly_rate = form.hourly_rate.data
        staff.hire_date = form.hire_date.data
        staff.status = form.status.data
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
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(status='active').order_by(Staff.name)]
    
    if form.validate_on_submit():
        shift = Shift(
            staff_id=form.staff_id.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            break_duration=form.break_duration.data or 0,
            notes=form.notes.data,
            created_by=current_user.id
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
    form.staff_id.choices = [(s.id, s.name) for s in Staff.query.filter_by(status='active').order_by(Staff.name)]
    
    if request.method == 'GET':
        form.staff_id.data = shift.staff_id
        form.start_time.data = shift.start_time
        form.end_time.data = shift.end_time
        form.break_duration.data = shift.break_duration
        form.notes.data = shift.notes
    
    if form.validate_on_submit():
        shift.staff_id = form.staff_id.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.break_duration = form.break_duration.data or 0
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
    staff_members = Staff.query.filter_by(status='active').order_by(Staff.name).all()
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
        color = staff_colors.get(position, '#6c757d')  # default gray
        
        events.append({
            'id': shift.id,
            'title': f"{shift.staff.name} ({shift.staff.position.capitalize()})",
            'start': shift.start_time.isoformat(),
            'end': shift.end_time.isoformat(),
            'color': color,
            'extendedProps': {
                'staffId': shift.staff_id,
                'staffName': shift.staff.name,
                'position': position,
                'notes': shift.notes,
                'breakDuration': shift.break_duration,
                'duration': shift.duration
            }
        })
    
    return jsonify(events)