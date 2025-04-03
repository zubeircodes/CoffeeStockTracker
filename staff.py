from datetime import datetime, timedelta
import json

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from sqlalchemy import and_

from app import db
from models import Staff, Shift, User
from forms import StaffForm, ShiftForm

# Create Blueprint
staff_bp = Blueprint('staff', __name__, url_prefix='/staff')

@staff_bp.route('/')
@login_required
def staff_dashboard():
    """
    Display staff dashboard with calendar
    """
    return render_template('staff/dashboard.html', title='Staff Dashboard')

@staff_bp.route('/list')
@login_required
def staff_list():
    """
    Display list of staff members
    """
    staff_members = Staff.query.all()
    form = StaffForm()
    
    # Count active shifts for each staff member
    now = datetime.utcnow()
    
    for staff_member in staff_members:
        active_shifts = Shift.query.filter(
            and_(
                Shift.staff_id == staff_member.id,
                Shift.start_time <= now,
                Shift.end_time >= now
            )
        ).count()
        
        staff_member.active_shifts = active_shifts
    
    return render_template('staff/list.html', 
                          title='Staff List', 
                          staff_members=staff_members,
                          form=form)

@staff_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_staff():
    """
    Create new staff member
    """
    form = StaffForm()
    
    if form.validate_on_submit():
        staff = Staff(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            position=form.position.data,
            role=form.role.data,
            phone=form.phone.data,
            color=form.color.data,
            hourly_rate=form.hourly_rate.data,
            hire_date=form.hire_date.data,
            is_active=form.is_active.data
        )
        
        # If the staff is linked to a user account, connect them
        # This could be extended to create a user account for the staff member
        
        db.session.add(staff)
        db.session.commit()
        flash(f'Staff member {staff.full_name} has been created.', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/create.html', title='Add Staff Member', form=form)

@staff_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    """
    Edit staff member
    """
    staff = Staff.query.get_or_404(id)
    form = StaffForm(obj=staff)
    
    if form.validate_on_submit():
        staff.first_name = form.first_name.data
        staff.last_name = form.last_name.data
        staff.position = form.position.data
        staff.role = form.role.data
        staff.phone = form.phone.data
        staff.color = form.color.data
        staff.hourly_rate = form.hourly_rate.data
        staff.hire_date = form.hire_date.data
        staff.is_active = form.is_active.data
        
        db.session.commit()
        flash(f'Staff member {staff.full_name} has been updated.', 'success')
        return redirect(url_for('staff.staff_list'))
    
    return render_template('staff/edit.html', title='Edit Staff Member', form=form, staff=staff)

@staff_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_staff(id):
    """
    Delete staff member
    """
    staff = Staff.query.get_or_404(id)
    
    # Check if there are shifts assigned to this staff member
    shift_count = Shift.query.filter_by(staff_id=staff.id).count()
    
    if shift_count > 0:
        flash(f'Cannot delete {staff.full_name}. There are {shift_count} shifts assigned to this staff member.', 'danger')
        return redirect(url_for('staff.staff_list'))
    
    db.session.delete(staff)
    db.session.commit()
    flash(f'Staff member {staff.full_name} has been deleted.', 'success')
    return redirect(url_for('staff.staff_list'))

@staff_bp.route('/shift/calendar')
@login_required
def shift_calendar():
    """
    Display staff shift calendar
    """
    staff_members = Staff.query.filter_by(is_active=True).all()
    return render_template('staff/calendar.html', 
                          title='Shift Calendar',
                          staff_members=staff_members)

@staff_bp.route('/shifts')
@login_required
def shifts_list():
    """
    Display list of shifts
    """
    shifts = Shift.query.order_by(Shift.start_time.desc()).all()
    now = datetime.utcnow()
    return render_template('staff/shifts.html', 
                          title='All Shifts',
                          shifts=shifts,
                          now=now)

@staff_bp.route('/shift/create', methods=['GET', 'POST'])
@login_required
def create_shift():
    """
    Create new shift
    """
    form = ShiftForm()
    
    # Populate staff dropdown
    form.staff_id.choices = [(s.id, s.full_name) for s in Staff.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Get recurring days from form data (request.form is a MultiDict that can have multiple values for the same key)
        recurring_days = request.form.getlist('recurring_days')
        
        shift = Shift(
            staff_id=form.staff_id.data,
            title=form.title.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            is_recurring=form.is_recurring.data,
            recurring_days=','.join(recurring_days) if recurring_days else None,
            notes=form.notes.data
        )
        
        db.session.add(shift)
        db.session.commit()
        flash('Shift has been created.', 'success')
        
        # Redirect to calendar if coming from there, otherwise to shift list
        next_page = request.args.get('next')
        if next_page and next_page == 'calendar':
            return redirect(url_for('staff.shift_calendar'))
        return redirect(url_for('staff.shifts_list'))
    
    return render_template('staff/create_shift.html', title='Add Shift', form=form)

@staff_bp.route('/shift/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_shift(id):
    """
    Edit shift
    """
    shift = Shift.query.get_or_404(id)
    form = ShiftForm(obj=shift)
    
    # Populate staff dropdown
    form.staff_id.choices = [(s.id, s.full_name) for s in Staff.query.filter_by(is_active=True).all()]
    
    # Parse recurring days
    if shift.recurring_days:
        form.recurring_days.data = shift.recurring_days.split(',')
    
    if form.validate_on_submit():
        # Get recurring days from form data
        recurring_days = request.form.getlist('recurring_days')
        
        shift.staff_id = form.staff_id.data
        shift.title = form.title.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.is_recurring = form.is_recurring.data
        shift.recurring_days = ','.join(recurring_days) if recurring_days else None
        shift.notes = form.notes.data
        
        db.session.commit()
        flash('Shift has been updated.', 'success')
        
        # Redirect to calendar if coming from there, otherwise to shift list
        next_page = request.args.get('next')
        if next_page and next_page == 'calendar':
            return redirect(url_for('staff.shift_calendar'))
        return redirect(url_for('staff.shifts_list'))
    
    return render_template('staff/edit_shift.html', title='Edit Shift', form=form, shift=shift)

@staff_bp.route('/shift/delete/<int:id>', methods=['POST'])
@login_required
def delete_shift(id):
    """
    Delete shift
    """
    shift = Shift.query.get_or_404(id)
    db.session.delete(shift)
    db.session.commit()
    flash('Shift has been deleted.', 'success')
    
    # Redirect to calendar if coming from there, otherwise to shift list
    next_page = request.args.get('next')
    if next_page and next_page == 'calendar':
        return redirect(url_for('staff.shift_calendar'))
    return redirect(url_for('staff.shifts_list'))

@staff_bp.route('/api/shifts', methods=['GET'])
@login_required
def get_shifts():
    """
    API endpoint to get shifts for calendar
    """
    # Get date range parameters from query string
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    # Default to current month if not provided
    now = datetime.utcnow()
    start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')) if start_str else datetime(now.year, now.month, 1)
    end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')) if end_str else datetime(now.year, now.month + 1, 1)
    
    # Query shifts within date range
    shifts = Shift.query.filter(
        and_(
            Shift.start_time >= start_date,
            Shift.start_time < end_date
        )
    ).all()
    
    # Format for FullCalendar
    events = []
    for shift in shifts:
        staff = Staff.query.get(shift.staff_id)
        if staff:
            event = {
                'id': shift.id,
                'title': f"{staff.full_name}: {shift.title}" if shift.title else staff.full_name,
                'start': shift.start_time.isoformat(),
                'end': shift.end_time.isoformat(),
                'backgroundColor': staff.color,
                'borderColor': staff.color,
                'extendedProps': {
                    'staff_id': staff.id,
                    'staff_name': staff.full_name,
                    'position': staff.position,
                    'notes': shift.notes,
                    'is_recurring': shift.is_recurring
                }
            }
            events.append(event)
    
    return jsonify(events)

@staff_bp.route('/api/active-shifts', methods=['GET'])
@login_required
def get_active_shifts():
    """
    API endpoint to get currently active shifts
    """
    now = datetime.utcnow()
    
    # Query currently active shifts
    active_shifts = db.session.query(Shift, Staff).join(Staff).\
        filter(
            and_(
                Shift.start_time <= now,
                Shift.end_time >= now
            )
        ).all()
    
    # Format for display
    result = []
    for shift, staff in active_shifts:
        result.append({
            'id': shift.id,
            'staff_id': staff.id,
            'staff_name': staff.full_name,
            'position': staff.position,
            'color': staff.color,
            'shift_title': shift.title,
            'start_time': shift.start_time.strftime('%H:%M'),
            'end_time': shift.end_time.strftime('%H:%M'),
            'duration_hours': shift.duration_hours,
            'remaining_minutes': int((shift.end_time - now).total_seconds() / 60)
        })
    
    return jsonify(result)