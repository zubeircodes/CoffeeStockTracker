import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///coffee_inventory.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Create all database tables
with app.app_context():
    # Import models here to avoid circular imports
    from models import User, Product, Vendor, InventoryTransaction
    db.create_all()

# Register blueprints
with app.app_context():
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from inventory import inventory as inventory_blueprint
    app.register_blueprint(inventory_blueprint)
    
    from reports import reports as reports_blueprint
    app.register_blueprint(reports_blueprint)
    
    from routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Add utility functions to template context
    from utils import (get_low_stock_products, get_products_by_category, 
                      get_inventory_value, get_transaction_history, 
                      format_currency, get_category_value_distribution,
                      get_transaction_summary)
    
    @app.context_processor
    def utility_processor():
        return {
            'get_low_stock_products': get_low_stock_products,
            'get_products_by_category': get_products_by_category,
            'get_inventory_value': get_inventory_value,
            'get_transaction_history': get_transaction_history,
            'format_currency': format_currency,
            'get_category_value_distribution': get_category_value_distribution,
            'get_transaction_summary': get_transaction_summary
        }
