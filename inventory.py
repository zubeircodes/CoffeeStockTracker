from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from models import Product, Category, Vendor, InventoryTransaction
from forms import ProductForm, CategoryForm, VendorForm, InventoryTransactionForm
from datetime import datetime

inventory = Blueprint('inventory', __name__)

@inventory.route('/inventory')
@login_required
def inventory_list():
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    query = Product.query
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%') | 
                             Product.sku.ilike(f'%{search_query}%'))
    
    # Apply sorting
    if sort_order == 'asc':
        query = query.order_by(getattr(Product, sort_by))
    else:
        query = query.order_by(desc(getattr(Product, sort_by)))
    
    products = query.all()
    return render_template('inventory_list.html', 
                          products=products, 
                          search_query=search_query,
                          sort_by=sort_by,
                          sort_order=sort_order)

@inventory.route('/inventory/create', methods=['GET', 'POST'])
@login_required
def create_product():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    form.vendor_id.choices = [(v.id, v.name) for v in Vendor.query.order_by('name')]
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            sku=form.sku.data,
            description=form.description.data,
            unit=form.unit.data,
            quantity=form.quantity.data,
            min_quantity=form.min_quantity.data,
            price=form.price.data,
            category_id=form.category_id.data,
            vendor_id=form.vendor_id.data
        )
        db.session.add(product)
        db.session.commit()
        
        # Create initial inventory transaction
        if form.quantity.data > 0:
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='adjustment',
                quantity=form.quantity.data,
                notes=f'Initial inventory for {product.name}',
                created_by=current_user.id
            )
            db.session.add(transaction)
            db.session.commit()
            
        flash(f'Product "{product.name}" has been created successfully.', 'success')
        return redirect(url_for('inventory.inventory_list'))
    
    return render_template('inventory_edit.html', form=form, title='Add New Product')

@inventory.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    form.vendor_id.choices = [(v.id, v.name) for v in Vendor.query.order_by('name')]
    
    if form.validate_on_submit():
        old_quantity = product.quantity
        
        product.name = form.name.data
        product.sku = form.sku.data
        product.description = form.description.data
        product.unit = form.unit.data
        product.min_quantity = form.min_quantity.data
        product.price = form.price.data
        product.category_id = form.category_id.data
        product.vendor_id = form.vendor_id.data
        
        # Check if quantity changed
        if old_quantity != form.quantity.data:
            product.quantity = form.quantity.data
            # Create adjustment transaction
            adjustment = form.quantity.data - old_quantity
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='adjustment',
                quantity=adjustment,
                notes=f'Manual adjustment: {old_quantity} -> {form.quantity.data}',
                created_by=current_user.id
            )
            db.session.add(transaction)
        
        db.session.commit()
        flash(f'Product "{product.name}" has been updated successfully.', 'success')
        return redirect(url_for('inventory.inventory_list'))
    
    return render_template('inventory_edit.html', form=form, product=product, title='Edit Product')

@inventory.route('/inventory/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    name = product.name
    
    # Delete associated transactions first
    InventoryTransaction.query.filter_by(product_id=id).delete()
    
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" has been deleted successfully.', 'success')
    return redirect(url_for('inventory.inventory_list'))

@inventory.route('/inventory/transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = InventoryTransactionForm()
    form.product_id.choices = [(p.id, p.name) for p in Product.query.order_by('name')]
    
    if form.validate_on_submit():
        product = Product.query.get(form.product_id.data)
        transaction = InventoryTransaction(
            product_id=form.product_id.data,
            transaction_type=form.transaction_type.data,
            quantity=form.quantity.data,
            notes=form.notes.data,
            transaction_date=form.transaction_date.data,
            created_by=current_user.id
        )
        
        # Update product quantity based on transaction type
        if form.transaction_type.data == 'purchase':
            product.quantity += form.quantity.data
        elif form.transaction_type.data == 'usage':
            if product.quantity < form.quantity.data:
                flash(f'Not enough stock available for {product.name}. Current: {product.quantity} {product.unit}', 'danger')
                return render_template('inventory_transaction.html', form=form, title='Add Transaction')
            product.quantity -= form.quantity.data
        elif form.transaction_type.data == 'adjustment':
            product.quantity = form.quantity.data
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Inventory transaction recorded successfully.', 'success')
        return redirect(url_for('inventory.inventory_list'))
    
    return render_template('inventory_transaction.html', form=form, title='Add Transaction')

# Category routes
@inventory.route('/categories')
@login_required
def category_list():
    categories = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=categories)

@inventory.route('/categories/create', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{category.name}" has been created successfully.', 'success')
        return redirect(url_for('inventory.category_list'))
    
    return render_template('category_edit.html', form=form, title='Add New Category')

@inventory.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash(f'Category "{category.name}" has been updated successfully.', 'success')
        return redirect(url_for('inventory.category_list'))
    
    return render_template('category_edit.html', form=form, category=category, title='Edit Category')

@inventory.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    
    # Check if category is used by products
    if len(category.products) > 0:
        flash(f'Cannot delete category "{category.name}" as it is assigned to products.', 'danger')
        return redirect(url_for('inventory.category_list'))
    
    name = category.name
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{name}" has been deleted successfully.', 'success')
    return redirect(url_for('inventory.category_list'))

# Vendor routes
@inventory.route('/vendors')
@login_required
def vendor_list():
    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template('vendors.html', vendors=vendors)

@inventory.route('/vendors/create', methods=['GET', 'POST'])
@login_required
def create_vendor():
    form = VendorForm()
    
    if form.validate_on_submit():
        vendor = Vendor(
            name=form.name.data,
            contact_name=form.contact_name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            notes=form.notes.data
        )
        db.session.add(vendor)
        db.session.commit()
        flash(f'Vendor "{vendor.name}" has been created successfully.', 'success')
        return redirect(url_for('inventory.vendor_list'))
    
    return render_template('vendor_edit.html', form=form, title='Add New Vendor')

@inventory.route('/vendors/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    form = VendorForm(obj=vendor)
    
    if form.validate_on_submit():
        vendor.name = form.name.data
        vendor.contact_name = form.contact_name.data
        vendor.email = form.email.data
        vendor.phone = form.phone.data
        vendor.address = form.address.data
        vendor.notes = form.notes.data
        db.session.commit()
        flash(f'Vendor "{vendor.name}" has been updated successfully.', 'success')
        return redirect(url_for('inventory.vendor_list'))
    
    return render_template('vendor_edit.html', form=form, vendor=vendor, title='Edit Vendor')

@inventory.route('/vendors/delete/<int:id>', methods=['POST'])
@login_required
def delete_vendor(id):
    vendor = Vendor.query.get_or_404(id)
    
    # Check if vendor is used by products
    if len(vendor.products) > 0:
        flash(f'Cannot delete vendor "{vendor.name}" as it is assigned to products.', 'danger')
        return redirect(url_for('inventory.vendor_list'))
    
    name = vendor.name
    db.session.delete(vendor)
    db.session.commit()
    flash(f'Vendor "{name}" has been deleted successfully.', 'success')
    return redirect(url_for('inventory.vendor_list'))
