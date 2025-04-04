from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', backref='vendor', lazy=True)
    
    def __repr__(self):
        return f'<Vendor {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), default='each')  # e.g., lb, kg, oz, each
    quantity = db.Column(db.Float, default=0.0)
    min_quantity = db.Column(db.Float, default=1.0)  # Low stock threshold
    price = db.Column(db.Float, default=0.0)  # Cost price
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('InventoryTransaction', backref='product', lazy=True)
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity
    
    def __repr__(self):
        return f'<Product {self.name}>'

class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'purchase', 'usage', 'adjustment'
    quantity = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # User relationship
    user = db.relationship('User', backref='transactions')
    
    def __repr__(self):
        return f'<Transaction {self.id} {self.transaction_type}>'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='sales')
    
    def __repr__(self):
        return f'<Sale {self.id} {self.product.name if self.product else "Unknown"}>'

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(20), nullable=True)  # For calendar display
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shifts = db.relationship('Shift', backref='staff', lazy=True)
    
    @property
    def name(self):
        """Combined name property"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return f"Staff #{self.id}"
            
    @property
    def status(self):
        """Status property for compatibility with templates"""
        return "active" if self.is_active else "inactive"
    
    def __repr__(self):
        return f'<Staff {self.name}>'
        
    def to_dict(self):
        """Convert staff object to dictionary for calendar events"""
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'role': self.role,
            'status': self.status
        }

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_days = db.Column(db.String(100), nullable=True)  # Comma-separated days (e.g., "0,1,4" for Mon,Tue,Fri)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Shift {self.id} for {self.staff.name if self.staff else "Unknown"}>'
    
    @property
    def shift_type(self):
        """Derive shift type from title or time of day"""
        if self.title and 'opening' in self.title.lower():
            return 'opening'
        elif self.title and 'closing' in self.title.lower():
            return 'closing'
        elif self.title and 'special' in self.title.lower():
            return 'special'
        # Determine by time
        if self.start_time:
            hour = self.start_time.hour
            if hour < 10:
                return 'opening'
            elif hour >= 15:
                return 'closing'
            else:
                return 'mid-day'
        return 'mid-day'  # Default
    
    @property
    def location(self):
        """Default location"""
        return 'Main Store'
    
    @property
    def status(self):
        """Determine status based on time"""
        now = datetime.utcnow()
        if self.end_time < now:
            return 'completed'
        elif self.start_time > now:
            return 'scheduled'
        else:
            return 'in-progress'
    
    def to_dict(self):
        """Convert shift object to dictionary for calendar events"""
        return {
            'id': self.id,
            'title': self.title or f"{self.staff.name if self.staff else 'Staff'} - {self.shift_type.capitalize()} Shift",
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'location': self.location,
            'status': self.status,
            'type': self.shift_type,
            'notes': self.notes,
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else "Unknown",
            'recurring': self.is_recurring
        }
