from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Category, Vendor, InventoryTransaction
from app import db

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
    
    # Get total vendor count
    vendor_count = Vendor.query.count()
    
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
    
    return render_template('dashboard.html', 
                          low_stock_items=low_stock_items,
                          recent_transactions=recent_transactions,
                          total_value=total_value,
                          product_count=product_count,
                          vendor_count=vendor_count,
                          category_data=category_data)

@main.route('/alerts')
@login_required
def alerts():
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    return render_template('alerts.html', low_stock_items=low_stock_items)
