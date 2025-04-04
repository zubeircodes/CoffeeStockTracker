from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Category, Vendor, InventoryTransaction, Sale, Staff, Shift
from app import db
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Get low stock items
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    
    # Get recent transactions
    recent_transactions = InventoryTransaction.query.order_by(
        InventoryTransaction.transaction_date.desc()).limit(5).all()
    
    # Get total inventory value
    total_value = db.session.query(db.func.sum(Product.quantity * Product.price)).scalar() or 0
    
    # Get staff on duty today
    staff_on_duty_count, staff_on_duty = get_staff_on_duty_today()
    
    # Get category distribution
    categories = Category.query.all()
    category_data = []
    for category in categories:
        product_count = len(category.products)
        if product_count > 0:
            category_data.append({
                'name': category.name,
                'count': product_count
            })
    
    # Get revenue data for dashboard
    # Check if we have any sales data
    sales_count = db.session.query(func.count(Sale.id)).scalar() or 0
    
    # Initialize revenue variables
    total_revenue = 0
    monthly_revenue = 0
    previous_month_revenue = 0
    revenue_change_percent = 0
    revenue_months = []
    revenue_values = []
    top_selling_products = []
    
    # Sample weekly transactions data (will be replaced with actual data later)
    weekly_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_transactions = [12, 15, 10, 18, 22, 30, 25]
    
    if sales_count > 0:
        # Get total revenue
        total_revenue = db.session.query(func.sum(Sale.total)).scalar() or 0
        
        # Get today's date and date ranges
        today = datetime.now()
        current_month_start = datetime(today.year, today.month, 1)
        previous_month_start = current_month_start - relativedelta(months=1)
        previous_month_end = current_month_start - relativedelta(days=1)
        
        # Get current month revenue
        monthly_revenue = db.session.query(func.sum(Sale.total)).filter(
            Sale.sale_date >= current_month_start
        ).scalar() or 0
        
        # Get previous month revenue
        previous_month_revenue = db.session.query(func.sum(Sale.total)).filter(
            Sale.sale_date >= previous_month_start,
            Sale.sale_date <= previous_month_end
        ).scalar() or 0
        
        # Calculate percent change
        if previous_month_revenue > 0:
            revenue_change_percent = ((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100
        
        # Get last 6 months of revenue data for chart
        for i in range(5, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = datetime(month_date.year, month_date.month, 1)
            if i > 0:
                # Use relativedelta to properly handle month overflow
                next_month_date = month_date + relativedelta(months=1)
                month_end = datetime(next_month_date.year, next_month_date.month, 1) - relativedelta(days=1)
            else:
                month_end = today
            
            month_revenue = db.session.query(func.sum(Sale.total)).filter(
                Sale.sale_date >= month_start,
                Sale.sale_date <= month_end
            ).scalar() or 0
            
            revenue_months.append(month_start.strftime('%b %Y'))
            revenue_values.append(float(month_revenue))
        
        # Get top 5 selling products
        top_selling_products = db.session.query(
            Product.name,
            func.sum(Sale.quantity).label('quantity_sold'),
            func.sum(Sale.total).label('revenue')
        ).join(Sale).group_by(Product.id).order_by(func.sum(Sale.total).desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          low_stock_items=low_stock_items,
                          recent_transactions=recent_transactions,
                          total_value=total_value,
                          category_data=category_data,
                          # Staff on duty data
                          staff_on_duty_count=staff_on_duty_count,
                          staff_on_duty=staff_on_duty,
                          # Revenue data
                          total_revenue=total_revenue,
                          monthly_revenue=monthly_revenue,
                          previous_month_revenue=previous_month_revenue,
                          revenue_change_percent=revenue_change_percent,
                          revenue_months=revenue_months,
                          revenue_values=revenue_values,
                          top_selling_products=top_selling_products,
                          has_sales_data=sales_count > 0,
                          # Weekly transactions data
                          weekly_days=weekly_days,
                          weekly_transactions=weekly_transactions)

def get_staff_on_duty_today():
    """
    Get staff members who are scheduled to work today
    Returns count of staff and list of staff members
    """
    today = datetime.now().date()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    
    # Get day of week for checking recurring shifts
    day_of_week = today.strftime("%a")
    
    # Query non-recurring shifts scheduled for today
    non_recurring_shifts = Shift.query.filter(
        Shift.is_recurring == False,
        Shift.start_time >= today_start,
        Shift.start_time <= today_end
    ).all()
    
    # Query recurring shifts that might be active today
    recurring_shifts = Shift.query.filter(
        Shift.is_recurring == True,
        Shift.recurring_days.contains(day_of_week)
    ).all()
    
    # Combine staff from both types of shifts
    staff_ids = set()
    shifts_today = []
    
    # Add staff from non-recurring shifts
    for shift in non_recurring_shifts:
        staff_ids.add(shift.staff_id)
        shifts_today.append(shift)
    
    # Add staff from recurring shifts
    for shift in recurring_shifts:
        # We don't have an end_date field in the model yet, so we include all recurring shifts
        staff_ids.add(shift.staff_id)
        shifts_today.append(shift)
    
    # Get actual staff objects
    staff_on_duty = Staff.query.filter(Staff.id.in_(staff_ids)).all() if staff_ids else []
    
    return len(staff_on_duty), staff_on_duty

@main.route('/alerts')
@login_required
def alerts():
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    return render_template('alerts.html', low_stock_items=low_stock_items)
