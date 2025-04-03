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
    try:
        # Check if we have any sales data
        sales_count = db.session.query(func.count(Sale.id)).scalar() or 0
    except Exception as e:
        # Handle database errors
        flash(f'Database error: {str(e)}. Please make sure your database is properly set up.', 'danger')
        return redirect(url_for('routes.index'))
    
    # Get statistics
    total_revenue = db.session.query(func.sum(Sale.total)).scalar() or 0
    
    # Get today's date for default end date
    today = datetime.now()
    
    # Get start of current month for default start date
    start_of_month = datetime(today.year, today.month, 1)
    
    # Format the data for Chart.js
    months = []
    revenue_data = []
    top_products = []
    category_revenue = []
    
    # Only fetch data if we have sales
    if sales_count > 0:
        print(f"Found {sales_count} sales records")
        
        # Get monthly revenue data for chart
        monthly_revenue = db.session.query(
            extract('year', Sale.sale_date).label('year'),
            extract('month', Sale.sale_date).label('month'),
            func.sum(Sale.total).label('revenue')
        ).group_by('year', 'month').order_by('year', 'month').all()
        
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
    else:
        # If no sales data, display a message
        flash('No sales data available. Please upload sales data to see revenue insights.', 'info')
    
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
            # Print debug information
            print(f"File name: {file.filename}")
            print(f"File content type: {file.content_type}")
            
            # Create file-like object from the file data
            file_content = file.stream.read().decode("utf-8")
            print(f"File content (first 200 chars): {file_content[:200]}")
            
            stream = StringIO(file_content)
            
            # Parse CSV content
            csv_data = csv.DictReader(stream)
            
            # Import the data
            records_added = 0
            records_skipped = 0
            
            # Convert to list to check if there are rows
            rows = list(csv_data)
            print(f"Number of rows in CSV: {len(rows)}")
            
            if len(rows) == 0:
                flash('No data found in the CSV file.', 'warning')
                return render_template('sales_upload.html', form=form, title='Upload Sales Data')
            
            # Print first row as debug info
            if rows:
                print(f"First row: {rows[0]}")
            
            for row in rows:
                try:
                    # Check if product exists
                    product_id = int(row.get('product_id', 0))
                    product = Product.query.get(product_id)
                    
                    if not product:
                        print(f"Product not found: {product_id}")
                        records_skipped += 1
                        continue
                    
                    # Create sale record
                    sale = Sale(
                        product_id=product_id,
                        quantity=float(row['quantity']),
                        unit_price=float(row['unit_price']),
                        total=float(row['total']),
                        sale_date=datetime.strptime(row['date'], '%Y-%m-%d')
                    )
                    
                    db.session.add(sale)
                    records_added += 1
                    print(f"Added sale record for product {product_id}")
                except (ValueError, KeyError) as e:
                    print(f"Error processing row: {e}")
                    records_skipped += 1
                    continue
            
            db.session.commit()
            print(f"Committed {records_added} records to database")
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
    # Default empty data structure
    data = {
        'labels': [],
        'datasets': [{
            'label': 'Revenue',
            'data': []
        }]
    }
    
    try:
        # Check if we have any sales data
        sales_count = db.session.query(func.count(Sale.id)).scalar() or 0
        
        # If no sales data, return empty structure
        if sales_count == 0:
            return jsonify(data)
        
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
        
        # Add data to the response structure
        for date, revenue in results:
            data['labels'].append(date.strftime(date_format))
            data['datasets'][0]['data'].append(float(revenue))
            
    except Exception as e:
        # Log the error but return empty data
        print(f"Error in sales_timeline_data: {str(e)}")
    
    return jsonify(data)

@sales.route('/api/sales/category')
@login_required
def sales_by_category_data():
    """
    API endpoint to get sales data by category for charts
    """
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
    
    try:
        # Check if we have any sales data
        sales_count = db.session.query(func.count(Sale.id)).scalar() or 0
        
        # If no sales data, return empty structure
        if sales_count == 0:
            return jsonify(data)
        
        # Get categories with their sales data
        results = db.session.query(
            Product.category_id,
            func.sum(Sale.total).label('revenue')
        ).join(Sale).group_by(Product.category_id).all()
        
        for category_id, revenue in results:
            try:
                # Handle case where category might have been deleted
                product = Product.query.get(category_id)
                if product and product.category:
                    category_name = product.category.name
                else:
                    category_name = 'Uncategorized'
                    
                data['labels'].append(category_name)
                data['datasets'][0]['data'].append(float(revenue))
            except Exception as e:
                print(f"Error processing category {category_id}: {e}")
                continue
    
    except Exception as e:
        # Log the error but return empty data
        print(f"Error in sales_by_category_data: {str(e)}")
    
    return jsonify(data)

@sales.route('/sales_report', methods=['GET', 'POST'])
@login_required
def sales_report():
    """
    Generate and display sales reports
    """
    form = ReportForm()
    
    try:
        # Check if we have any sales data
        sales_count = db.session.query(func.count(Sale.id)).scalar() or 0
        
        if sales_count == 0 and request.method == 'GET':
            flash('No sales data available. Please upload sales data first.', 'info')
            return redirect(url_for('sales.upload_sales'))
        
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
                try:
                    # Get sales with product details
                    sales_data = query.order_by(Sale.sale_date.desc()).all()
                    
                    if not sales_data:
                        flash('No sales data found for the selected date range.', 'warning')
                        return render_template('sales_report_form.html', form=form, title='Generate Sales Report')
                    
                    return render_template('sales_report.html',
                                       title='Sales Report',
                                       sales=sales_data,
                                       start_date=start_date,
                                       end_date=end_date)
                except Exception as e:
                    flash(f'Error generating sales report: {str(e)}', 'danger')
                    print(f"Error in sales report generation: {str(e)}")
                    return render_template('sales_report_form.html', form=form, title='Generate Sales Report')
        
    except Exception as e:
        flash(f'Database error: {str(e)}. Please make sure your database is properly set up.', 'danger')
        print(f"Error in sales_report: {str(e)}")
        return redirect(url_for('routes.index'))
    
    return render_template('sales_report_form.html', form=form, title='Generate Sales Report')