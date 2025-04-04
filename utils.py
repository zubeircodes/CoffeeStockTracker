from datetime import datetime, timedelta
from models import Product, Category, InventoryTransaction
from app import db
from sqlalchemy import func

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
