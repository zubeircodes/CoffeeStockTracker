from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Category, Vendor, InventoryTransaction, Sale
from app import db
from sqlalchemy import func, extract
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils import get_employees_working_today

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
    
    # Get total product count
    product_count = Product.query.count()
    
    # Get the number of employees working today
    employees_working = get_employees_working_today()
    
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
                          product_count=product_count,
                          employees_working=employees_working,
                          category_data=category_data,
                          datetime=datetime,
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

@main.route('/alerts')
@login_required
def alerts():
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    return render_template('alerts.html', low_stock_items=low_stock_items)
