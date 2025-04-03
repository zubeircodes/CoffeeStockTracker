from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms import SelectField, FloatField, HiddenField, DateField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from models import User, Product, Vendor

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    sku = StringField('SKU', validators=[Length(max=50)])
    description = TextAreaField('Description')
    unit = StringField('Unit (e.g., lb, oz, each)', validators=[DataRequired(), Length(max=20)])
    quantity = FloatField('Current Quantity', validators=[DataRequired()])
    min_quantity = FloatField('Low Stock Threshold', validators=[DataRequired()])
    price = FloatField('Cost Price ($)', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int)
    vendor_id = SelectField('Vendor', coerce=int)
    submit = SubmitField('Save Product')

class VendorForm(FlaskForm):
    name = StringField('Vendor Name', validators=[DataRequired(), Length(max=100)])
    contact_name = StringField('Contact Person', validators=[Length(max=100)])
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Length(max=20)])
    address = TextAreaField('Address')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Vendor')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    submit = SubmitField('Save Category')

class InventoryTransactionForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', 
                                choices=[('purchase', 'Purchase'), 
                                         ('usage', 'Usage'), 
                                         ('adjustment', 'Adjustment')],
                                validators=[DataRequired()])
    quantity = FloatField('Quantity', validators=[DataRequired()])
    notes = TextAreaField('Notes')
    transaction_date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Submit')

class ReportForm(FlaskForm):
    report_type = SelectField('Report Type', 
                            choices=[('low_stock', 'Low Stock Items'), 
                                     ('inventory_value', 'Inventory Value'), 
                                     ('transactions', 'Recent Transactions'),
                                     ('sales', 'Sales Report')],
                            validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Generate Report')
    
class SalesUploadForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[
        DataRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload Sales Data')
