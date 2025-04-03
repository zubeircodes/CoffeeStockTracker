import os
import csv
from datetime import datetime
from io import StringIO
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, extract
from app import db
from models import Product, Sale
from forms import SalesUploadForm, ReportForm

sales = Blueprint('sales', __name__)

@sales.route('/revenue')
@login_required
def revenue_dashboard():
    """
    Display revenue dashboard with visualizations
    """
    # Get statistics
    total_revenue = db.session.query(func.sum(Sale.total)).scalar() or 0
    
    # Get today's date for default end date
    today = datetime.now()
    
    # Get start of current month for default start date
    start_of_month = datetime(today.year, today.month, 1)
    
    # Get monthly revenue data for chart
    monthly_revenue = db.session.query(
        extract('year', Sale.sale_date).label('year'),
        extract('month', Sale.sale_date).label('month'),
        func.sum(Sale.total).label('revenue')
    ).group_by('year', 'month').order_by('year', 'month').all()
    
    # Format the data for Chart.js
    months = []
    revenue_data = []
    
    for item in monthly_revenue:
        month_name = datetime(int(item.year), int(item.month), 1).strftime('%b %Y')
        months.append(month_name)
        revenue_data.append(float(item.revenue))
    
    # Get top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(Sale.quantity).label('total_quantity'),
        func.sum(Sale.total).label('total_revenue')
    ).join(Sale).group_by(Product.name).order_by(func.sum(Sale.total).desc()).limit(5).all()
    
    # Calculate revenue by category
    category_revenue = db.session.query(
        Product.category_id,
        func.sum(Sale.total).label('revenue')
    ).join(Sale).group_by(Product.category_id).all()
    
    return render_template('revenue_dashboard.html',
                           title='Revenue Dashboard',
                           total_revenue=total_revenue,
                           months=months,
                           revenue_data=revenue_data,
                           top_products=top_products,
                           category_revenue=category_revenue)

@sales.route('/sales_upload', methods=['GET', 'POST'])
@login_required
def upload_sales():
    """
    Handle upload of sales data from CSV file
    """
    form = SalesUploadForm()
    
    if form.validate_on_submit():
        # Get the uploaded file
        file = form.csv_file.data
        
        # Process the file
        try:
            # Create file-like object from the file data
            stream = StringIO(file.stream.read().decode("utf-8"))
            
            # Parse CSV content
            csv_data = csv.DictReader(stream)
            
            # Import the data
            records_added = 0
            records_skipped = 0
            for row in csv_data:
                try:
                    # Check if product exists
                    product = Product.query.get(int(row['product_id']))
                    if not product:
                        records_skipped += 1
                        continue
                    
                    # Create sale record
                    sale = Sale(
                        product_id=int(row['product_id']),
                        quantity=float(row['quantity']),
                        unit_price=float(row['unit_price']),
                        total=float(row['total']),
                        sale_date=datetime.strptime(row['date'], '%Y-%m-%d')
                    )
                    
                    db.session.add(sale)
                    records_added += 1
                except (ValueError, KeyError) as e:
                    records_skipped += 1
                    continue
            
            db.session.commit()
            flash(f'Successfully imported {records_added} sales records. {records_skipped} records were skipped.', 'success')
            
            return redirect(url_for('sales.revenue_dashboard'))
            
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'danger')
    
    return render_template('sales_upload.html', form=form, title='Upload Sales Data')

@sales.route('/api/sales/timeline')
@login_required
def sales_timeline_data():
    """
    API endpoint to get sales timeline data for charts
    """
    # Get parameters
    period = request.args.get('period', 'monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Query base
    query = db.session.query(
        Sale.sale_date,
        func.sum(Sale.total).label('revenue')
    )
    
    # Apply date filters if provided
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Sale.sale_date >= start)
        except ValueError:
            pass
            
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Sale.sale_date <= end)
        except ValueError:
            pass
    
    # Group by the appropriate time period
    if period == 'daily':
        query = query.group_by(func.date(Sale.sale_date))
        date_format = '%Y-%m-%d'
    elif period == 'weekly':
        query = query.group_by(func.strftime('%Y-%W', Sale.sale_date))
        date_format = 'Week %W, %Y'
    else:  # monthly
        query = query.group_by(func.strftime('%Y-%m', Sale.sale_date))
        date_format = '%b %Y'
    
    # Execute the query
    results = query.order_by(Sale.sale_date).all()
    
    # Format the data for the chart
    data = {
        'labels': [],
        'datasets': [{
            'label': 'Revenue',
            'data': []
        }]
    }
    
    for date, revenue in results:
        data['labels'].append(date.strftime(date_format))
        data['datasets'][0]['data'].append(float(revenue))
    
    return jsonify(data)

@sales.route('/api/sales/category')
@login_required
def sales_by_category_data():
    """
    API endpoint to get sales data by category for charts
    """
    # Get categories with their sales data
    results = db.session.query(
        Product.category_id,
        func.sum(Sale.total).label('revenue')
    ).join(Sale).group_by(Product.category_id).all()
    
    # Format data for charts
    data = {
        'labels': [],
        'datasets': [{
            'data': [],
            'backgroundColor': [
                '#4e73df', '#1cc88a', '#36b9cc',
                '#f6c23e', '#e74a3b', '#858796',
                '#5a5c69', '#6610f2', '#6f42c1'
            ]
        }]
    }
    
    for category_id, revenue in results:
        category = Product.query.get(category_id).category.name if category_id else 'Uncategorized'
        data['labels'].append(category)
        data['datasets'][0]['data'].append(float(revenue))
    
    return jsonify(data)

@sales.route('/sales_report', methods=['GET', 'POST'])
@login_required
def sales_report():
    """
    Generate and display sales reports
    """
    form = ReportForm()
    
    if form.validate_on_submit():
        # Get parameters
        report_type = form.report_type.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        # Base query
        query = Sale.query
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        if end_date:
            query = query.filter(Sale.sale_date <= end_date)
        
        # Get results based on report type
        if report_type == 'sales':
            # Get sales with product details
            sales_data = query.order_by(Sale.sale_date.desc()).all()
            
            return render_template('sales_report.html',
                                   title='Sales Report',
                                   sales=sales_data,
                                   start_date=start_date,
                                   end_date=end_date)
    
    return render_template('sales_report_form.html', form=form, title='Generate Sales Report')