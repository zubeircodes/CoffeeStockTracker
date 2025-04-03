import os
import csv
import uuid
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc, extract
from app import db
from models import Sale, SaleItem, Product, PaymentType
from forms import UploadSalesForm, RevenueReportForm

revenue = Blueprint('revenue', __name__)

# Utility functions
def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

def process_clover_csv(file_path, user_id):
    """
    Process a Clover CSV file and save the data to the database
    Returns (success, message, import_batch_id)
    """
    try:
        # Generate a unique batch ID for this import
        import_batch_id = str(uuid.uuid4())
        
        # Read CSV file using pandas
        df = pd.read_csv(file_path)
        
        # Basic validation - check if required columns exist
        required_columns = ['Order ID', 'Time', 'Item Name', 'Price', 'Quantity']
        for col in required_columns:
            if col not in df.columns:
                return False, f"Missing required column: {col}", None
        
        # Group by Order ID to create Sale records
        order_groups = df.groupby('Order ID')
        
        # Track successfully processed orders
        processed_orders = 0
        
        for order_id, order_items in order_groups:
            # Get order date from the first item (same for all items in an order)
            try:
                order_date_str = order_items['Time'].iloc[0]
                
                # Try different date formats - Clover might use different formats
                date_formats = [
                    '%Y-%m-%d %H:%M:%S', 
                    '%m/%d/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S'
                ]
                
                sale_date = None
                for date_format in date_formats:
                    try:
                        sale_date = datetime.strptime(order_date_str, date_format)
                        break
                    except ValueError:
                        continue
                
                if not sale_date:
                    return False, f"Could not parse date format in row for order {order_id}", None
                
            except (KeyError, IndexError) as e:
                return False, f"Error processing date for order {order_id}: {str(e)}", None
            
            # Calculate order totals
            total_amount = order_items['Price'].sum() if 'Price' in order_items.columns else 0
            tax_amount = order_items['Tax'].sum() if 'Tax' in order_items.columns else 0
            discount_amount = order_items['Discount'].sum() if 'Discount' in order_items.columns else 0
            
            # Determine payment type if available
            payment_type = PaymentType.OTHER
            if 'Payment Type' in order_items.columns:
                payment_str = str(order_items['Payment Type'].iloc[0]).lower()
                if 'credit' in payment_str or 'card' in payment_str:
                    payment_type = PaymentType.CREDIT
                elif 'cash' in payment_str:
                    payment_type = PaymentType.CASH
                elif 'mobile' in payment_str or 'app' in payment_str:
                    payment_type = PaymentType.MOBILE
            
            # Check if this order already exists
            existing_sale = Sale.query.filter_by(order_id=str(order_id)).first()
            if existing_sale:
                # Skip this order or update it if needed
                continue
            
            # Create new Sale record
            sale = Sale(
                order_id=str(order_id),
                sale_date=sale_date,
                payment_type=payment_type,
                total_amount=total_amount,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                uploaded_by=user_id,
                import_batch=import_batch_id
            )
            db.session.add(sale)
            db.session.flush()  # Get the sale ID for item relationships
            
            # Process each item in the order
            for _, item in order_items.iterrows():
                product_name = item.get('Item Name', 'Unknown Product')
                unit_price = float(item.get('Price', 0)) / float(item.get('Quantity', 1))
                quantity = float(item.get('Quantity', 1))
                
                # Try to match with inventory product
                sku = item.get('SKU', None)
                product_id = None
                
                if sku:
                    # Try to match by SKU
                    product = Product.query.filter_by(sku=sku).first()
                    if product:
                        product_id = product.id
                else:
                    # Try to match by name
                    product = Product.query.filter(Product.name.ilike(f"%{product_name}%")).first()
                    if product:
                        product_id = product.id
                
                # Create SaleItem record
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_name=product_name,
                    sku=sku,
                    quantity=quantity,
                    unit_price=unit_price,
                    product_id=product_id
                )
                db.session.add(sale_item)
            
            processed_orders += 1
        
        # Commit all changes to the database
        db.session.commit()
        
        return True, f"Successfully imported {processed_orders} orders with {len(df)} items", import_batch_id
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error processing CSV: {str(e)}", None

# Routes
@revenue.route('/revenue-dashboard')
@login_required
def revenue_dashboard():
    """Display the revenue dashboard with sales data summaries and charts"""
    # Default to past 30 days if no date range specified
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get form for filtering
    form = RevenueReportForm()
    
    # Get sales data for the period
    sales = Sale.query.filter(
        Sale.sale_date.between(start_date, end_date)
    ).order_by(Sale.sale_date.desc()).all()
    
    # Get total revenue for the period
    total_revenue = sum(sale.total_amount for sale in sales)
    
    # Calculate average sale amount
    avg_sale = total_revenue / len(sales) if sales else 0
    
    # Get number of transactions
    transaction_count = len(sales)
    
    # Get top selling products
    top_products = db.session.query(
        SaleItem.product_name, 
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.quantity * SaleItem.unit_price).label('total_revenue')
    ).join(Sale).filter(
        Sale.sale_date.between(start_date, end_date)
    ).group_by(SaleItem.product_name).order_by(
        func.sum(SaleItem.quantity * SaleItem.unit_price).desc()
    ).limit(10).all()
    
    # Get daily revenue for chart
    daily_revenue = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.sum(Sale.total_amount).label('revenue')
    ).filter(
        Sale.sale_date.between(start_date, end_date)
    ).group_by(func.date(Sale.sale_date)).order_by(
        func.date(Sale.sale_date)
    ).all()
    
    # Format data for charts
    chart_labels = [day.date.strftime('%Y-%m-%d') for day in daily_revenue]
    chart_data = [float(day.revenue) for day in daily_revenue]
    
    # Format top products for chart
    product_labels = [product.product_name for product in top_products]
    product_data = [float(product.total_revenue) for product in top_products]
    
    # Get payment type distribution
    payment_data = db.session.query(
        Sale.payment_type,
        func.sum(Sale.total_amount).label('amount')
    ).filter(
        Sale.sale_date.between(start_date, end_date)
    ).group_by(Sale.payment_type).all()
    
    payment_labels = [payment.payment_type.name for payment in payment_data]
    payment_values = [float(payment.amount) for payment in payment_data]
    
    return render_template('revenue_dashboard.html',
                          title='Revenue Dashboard',
                          sales=sales,
                          total_revenue=total_revenue,
                          avg_sale=avg_sale,
                          transaction_count=transaction_count,
                          top_products=top_products,
                          chart_labels=chart_labels,
                          chart_data=chart_data,
                          product_labels=product_labels,
                          product_data=product_data,
                          payment_labels=payment_labels,
                          payment_values=payment_values,
                          start_date=start_date,
                          end_date=end_date,
                          form=form)

@revenue.route('/upload-sales', methods=['GET', 'POST'])
@login_required
def upload_sales():
    """Handle CSV file uploads"""
    form = UploadSalesForm()
    
    if form.validate_on_submit():
        # Check if the post request has the file part
        if 'sales_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['sales_file']
        
        # If user does not select file, browser submits an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Save file temporarily
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            
            # Process the file
            success, message, batch_id = process_clover_csv(temp_path, current_user.id)
            
            # Remove the temporary file
            os.remove(temp_path)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('revenue.revenue_dashboard'))
            else:
                flash(message, 'danger')
                return redirect(request.url)
    
    return render_template('upload_sales.html', title='Upload Sales Data', form=form)

@revenue.route('/api/revenue-data')
@login_required
def revenue_data():
    """API endpoint to get revenue data for charts"""
    # Parse query parameters
    days = request.args.get('days', type=int, default=30)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get daily revenue
    daily_revenue = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.sum(Sale.total_amount).label('revenue')
    ).filter(
        Sale.sale_date.between(start_date, end_date)
    ).group_by(func.date(Sale.sale_date)).order_by(
        func.date(Sale.sale_date)
    ).all()
    
    # Format data for JSON response
    data = {
        'labels': [day.date.strftime('%Y-%m-%d') for day in daily_revenue],
        'revenue': [float(day.revenue) for day in daily_revenue]
    }
    
    return jsonify(data)

@revenue.route('/sales-list')
@login_required
def sales_list():
    """Display a list of all sales transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get sales with pagination
    sales = Sale.query.order_by(Sale.sale_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('sales_list.html', 
                          title='Sales Transactions',
                          sales=sales)

@revenue.route('/sale-detail/<int:id>')
@login_required
def sale_detail(id):
    """Display details of a specific sale"""
    sale = Sale.query.get_or_404(id)
    
    return render_template('sale_detail.html',
                          title=f'Sale #{sale.order_id}',
                          sale=sale)