from datetime import datetime, timedelta, date
from models import Product, Category, InventoryTransaction, Staff, Shift
from app import db
from sqlalchemy import func, and_, or_, extract

def get_low_stock_products():
    """
    Returns products that are below their minimum stock level
    """
    return Product.query.filter(Product.quantity <= Product.min_quantity).all()

def get_products_by_category():
    """
    Returns a dictionary of products grouped by category
    """
    categories = Category.query.all()
    result = {}
    
    for category in categories:
        result[category.name] = category.products
    
    return result

def get_inventory_value():
    """
    Calculate the total value of inventory
    """
    total_value = db.session.query(func.sum(Product.price * Product.quantity)).scalar() or 0
    return total_value

def get_transaction_history(days=7):
    """
    Get transaction history for the last specified number of days
    """
    start_date = datetime.now() - timedelta(days=days)
    transactions = InventoryTransaction.query.filter(
        InventoryTransaction.transaction_date >= start_date
    ).order_by(InventoryTransaction.transaction_date.desc()).all()
    
    return transactions

def format_currency(value):
    """
    Format a value as currency
    """
    return f"${value:.2f}"

def get_category_value_distribution():
    """
    Get total inventory value by category
    """
    categories = Category.query.all()
    distribution = []
    
    for category in categories:
        total = sum(p.quantity * p.price for p in category.products)
        if total > 0:
            distribution.append({
                'name': category.name,
                'value': total
            })
    
    return distribution

def get_transaction_summary(days=30):
    """
    Get summary of transactions by type for the last specified number of days
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Get purchases
    purchases = db.session.query(func.sum(InventoryTransaction.quantity)).filter(
        InventoryTransaction.transaction_type == 'purchase',
        InventoryTransaction.transaction_date >= start_date
    ).scalar() or 0
    
    # Get usage
    usage = db.session.query(func.sum(InventoryTransaction.quantity)).filter(
        InventoryTransaction.transaction_type == 'usage',
        InventoryTransaction.transaction_date >= start_date
    ).scalar() or 0
    
    # Get adjustments
    adjustments = db.session.query(func.sum(InventoryTransaction.quantity)).filter(
        InventoryTransaction.transaction_type == 'adjustment',
        InventoryTransaction.transaction_date >= start_date
    ).scalar() or 0
    
    return {
        'purchases': purchases,
        'usage': usage,
        'adjustments': adjustments
    }

def get_employees_working_today():
    """
    Count the number of employees scheduled to work today
    This counts staff with non-recurring shifts today plus staff with recurring shifts on this day of week
    """
    today = date.today()
    day_of_week = today.strftime('%a')  # Returns 'Mon', 'Tue', etc.
    
    # Start and end of today
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Query for both non-recurring shifts today and recurring shifts for this day of week
    shifts_today = Shift.query.filter(
        or_(
            # Non-recurring shifts on today's date
            and_(
                Shift.start_time >= today_start,
                Shift.start_time <= today_end,
                Shift.is_recurring == False
            ),
            # Recurring shifts that include this day of week
            and_(
                Shift.is_recurring == True,
                Shift.recurring_days.like(f'%{day_of_week}%')
            )
        )
    ).all()
    
    # Get distinct staff IDs scheduled today
    staff_ids = set()
    for shift in shifts_today:
        staff_ids.add(shift.staff_id)
    
    return len(staff_ids)
