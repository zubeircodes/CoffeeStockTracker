from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms import SelectField, FloatField, HiddenField, DateField, EmailField, DateTimeField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, NumberRange
from models import User, Product, Vendor, Staff

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

class StaffForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[Length(max=20)])
    position = SelectField('Position', 
                          choices=[('barista', 'Barista'), 
                                   ('manager', 'Manager'), 
                                   ('cashier', 'Cashier'),
                                   ('cook', 'Cook'),
                                   ('server', 'Server')],
                          validators=[DataRequired()])
    role = SelectField('Role', 
                      choices=[('employee', 'Employee'), 
                               ('supervisor', 'Supervisor'), 
                               ('manager', 'Manager')],
                      validators=[DataRequired()])
    hourly_rate = FloatField('Hourly Rate ($)', validators=[DataRequired(), NumberRange(min=0)])
    hire_date = DateField('Hire Date', format='%Y-%m-%d', validators=[DataRequired()])
    is_active = BooleanField('Active')
    color = StringField('Calendar Color', validators=[Length(max=50)])
    submit = SubmitField('Save Staff')
    
    def __init__(self, *args, **kwargs):
        super(StaffForm, self).__init__(*args, **kwargs)
        self.id = HiddenField('id')
        
class ShiftForm(FlaskForm):
    staff_id = SelectField('Staff Member', coerce=int, validators=[DataRequired()])
    title = StringField('Shift Title', validators=[Length(max=100)])
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    is_recurring = BooleanField('Recurring Shift')
    recurring_days = StringField('Recurring Days (e.g., Mon,Wed,Fri)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Shift')
    
    def validate_end_time(self, end_time):
        if self.start_time.data and end_time.data:
            if end_time.data <= self.start_time.data:
                raise ValidationError('End time must be after start time')
