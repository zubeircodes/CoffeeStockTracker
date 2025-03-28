from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required
from app import db
from models import Product, Category, Vendor, InventoryTransaction
from forms import ReportForm
from datetime import datetime, timedelta
import pandas as pd
import io
import tempfile
import os

reports = Blueprint('reports', __name__)

@reports.route('/reports', methods=['GET', 'POST'])
@login_required
def report_dashboard():
    form = ReportForm()
    
    # Default to last 7 days if no dates provided
    if not form.start_date.data:
        form.start_date.data = datetime.today() - timedelta(days=7)
    if not form.end_date.data:
        form.end_date.data = datetime.today()
    
    report_data = None
    report_type = request.args.get('report_type', '')
    
    if form.validate_on_submit() or report_type:
        report_type = form.report_type.data if form.validate_on_submit() else report_type
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        if report_type == 'low_stock':
            report_data = generate_low_stock_report()
        elif report_type == 'inventory_value':
            report_data = generate_inventory_value_report()
        elif report_type == 'transactions':
            report_data = generate_transaction_report(start_date, end_date)
    
    return render_template('reports.html', form=form, report_data=report_data, report_type=report_type)

@reports.route('/reports/export/<report_type>')
@login_required
def export_report(report_type):
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else (datetime.today() - timedelta(days=7))
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.today()
    
    if report_type == 'low_stock':
        df = create_low_stock_dataframe()
        filename = 'low_stock_report.csv'
    elif report_type == 'inventory_value':
        df = create_inventory_value_dataframe()
        filename = 'inventory_value_report.csv'
    elif report_type == 'transactions':
        df = create_transaction_dataframe(start_date, end_date)
        filename = 'transaction_report.csv'
    else:
        flash('Invalid report type.', 'danger')
        return redirect(url_for('reports.report_dashboard'))
    
    # Create a BytesIO object
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Create a tempfile to return
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
        temp.write(output.getvalue())
        temp_path = temp.name
    
    return send_file(
        temp_path,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

def generate_low_stock_report():
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    return {
        'title': 'Low Stock Items Report',
        'headers': ['Name', 'SKU', 'Current Qty', 'Min Qty', 'Unit', 'Vendor'],
        'data': [
            [
                p.name,
                p.sku or '-',
                p.quantity,
                p.min_quantity,
                p.unit,
                p.vendor.name if p.vendor else '-'
            ] for p in low_stock_items
        ]
    }

def generate_inventory_value_report():
    products = Product.query.all()
    total_value = sum(p.quantity * p.price for p in products)
    
    by_category = {}
    categories = Category.query.all()
    
    for category in categories:
        category_value = sum(p.quantity * p.price for p in category.products)
        if category_value > 0:
            by_category[category.name] = category_value
    
    return {
        'title': 'Inventory Value Report',
        'headers': ['Name', 'SKU', 'Quantity', 'Unit', 'Price', 'Total Value'],
        'data': [
            [
                p.name,
                p.sku or '-',
                p.quantity,
                p.unit,
                f'${p.price:.2f}',
                f'${p.quantity * p.price:.2f}'
            ] for p in products
        ],
        'summary': {
            'total_value': f'${total_value:.2f}',
            'by_category': {name: f'${value:.2f}' for name, value in by_category.items()}
        }
    }

def generate_transaction_report(start_date, end_date):
    # Add one day to end_date to include the end_date in the query
    end_date = end_date + timedelta(days=1)
    
    transactions = InventoryTransaction.query.filter(
        InventoryTransaction.transaction_date >= start_date,
        InventoryTransaction.transaction_date < end_date
    ).order_by(InventoryTransaction.transaction_date.desc()).all()
    
    return {
        'title': f'Transaction Report ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})',
        'headers': ['Date', 'Product', 'Type', 'Quantity', 'Notes'],
        'data': [
            [
                t.transaction_date.strftime('%Y-%m-%d'),
                t.product.name,
                t.transaction_type.capitalize(),
                t.quantity,
                t.notes or '-'
            ] for t in transactions
        ]
    }

def create_low_stock_dataframe():
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    data = []
    
    for p in low_stock_items:
        data.append({
            'Name': p.name,
            'SKU': p.sku or '-',
            'Current Quantity': p.quantity,
            'Minimum Quantity': p.min_quantity,
            'Unit': p.unit,
            'Vendor': p.vendor.name if p.vendor else '-',
            'Category': p.category.name if p.category else '-',
            'Price': p.price
        })
    
    return pd.DataFrame(data)

def create_inventory_value_dataframe():
    products = Product.query.all()
    data = []
    
    for p in products:
        data.append({
            'Name': p.name,
            'SKU': p.sku or '-',
            'Quantity': p.quantity,
            'Unit': p.unit,
            'Unit Price': p.price,
            'Total Value': p.quantity * p.price,
            'Category': p.category.name if p.category else '-',
            'Vendor': p.vendor.name if p.vendor else '-'
        })
    
    return pd.DataFrame(data)

def create_transaction_dataframe(start_date, end_date):
    # Add one day to end_date to include the end_date in the query
    end_date = end_date + timedelta(days=1)
    
    transactions = InventoryTransaction.query.filter(
        InventoryTransaction.transaction_date >= start_date,
        InventoryTransaction.transaction_date < end_date
    ).order_by(InventoryTransaction.transaction_date.desc()).all()
    
    data = []
    
    for t in transactions:
        data.append({
            'Date': t.transaction_date.strftime('%Y-%m-%d'),
            'Product': t.product.name,
            'SKU': t.product.sku or '-',
            'Transaction Type': t.transaction_type.capitalize(),
            'Quantity': t.quantity,
            'Unit': t.product.unit,
            'Notes': t.notes or '-'
        })
    
    return pd.DataFrame(data)
