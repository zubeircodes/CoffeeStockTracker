from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum

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

class PaymentType(enum.Enum):
    CREDIT = 'credit'
    CASH = 'cash'
    MOBILE = 'mobile'
    OTHER = 'other'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False)
    payment_type = db.Column(db.Enum(PaymentType), default=PaymentType.CREDIT)
    total_amount = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    import_batch = db.Column(db.String(100))  # To track which CSV import batch this came from
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade="all, delete-orphan")
    user = db.relationship('User', backref='sales')
    
    @property
    def net_amount(self):
        """Calculate net amount after discounts but before tax"""
        return self.total_amount - self.discount_amount
    
    @property
    def item_count(self):
        """Get the total number of items sold in this sale"""
        return sum(item.quantity for item in self.items)
    
    def __repr__(self):
        return f'<Sale {self.order_id} {self.sale_date}>'

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50))
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)  # Link to inventory if matched
    
    # Relationship to Product (if matched)
    product = db.relationship('Product', backref='sales')
    
    @property
    def total_price(self):
        """Calculate total price for this line item"""
        return self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<SaleItem {self.product_name} ({self.quantity})>'
