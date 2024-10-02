# Imports
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify , send_file, make_response
from xhtml2pdf import pisa
import pdfkit
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError  # Import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate  # Include Flask-Migrate for migrations
from datetime import datetime
from weasyprint import HTML

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CSRF Protection
csrf = CSRFProtect(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Models
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(100), nullable=False)
    org_type = db.Column(db.String(50), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    gst_number = db.Column(db.String(15), nullable=True)  # GST Number is optional
    business_type = db.Column(db.String(50), nullable=True)  # Add this line to define business_type

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    product_code = db.Column(db.String(50), nullable=False, unique=True)
    sku = db.Column(db.String(50), nullable=True)  # Include SKU
    unit = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., Consumable, Trading, etc.
    product_type = db.Column(db.String(50), nullable=False)  # e.g., Finished Product, Service, Raw Material
    brand = db.Column(db.String(50), nullable=True)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=True)
    quantity_in_stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=True, default=10)
    gst_rate = db.Column(db.Float, nullable=True)
    hsn_code = db.Column(db.String(20), nullable=True)
    supplier = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add organization_id as a Foreign Key
    organization_id = db.Column(db.Integer, db.ForeignKey('setup_organization.id'), nullable=False)

    # Establish relationship with SetupOrganization
    organization = db.relationship('SetupOrganization', backref=db.backref('products', lazy=True))

# app.py or models.py

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    gst_number = db.Column(db.String(15), nullable=True)  # GST Number is optional
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    organization = db.relationship('Organization', backref=db.backref('customers', lazy=True))

    def __repr__(self):
        return f"<Customer {self.customer_name} - {self.company_name}>"


class SetupOrganization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(100), nullable=False)
    gst_number = db.Column(db.String(15), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    # contact_person = db.Column(db.String(100), nullable=False)
    org_type = db.Column(db.String(50), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('setup_organization.id'), nullable=False)

    organization = db.relationship('SetupOrganization', backref=db.backref('users', lazy=True))


class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    organization = db.relationship('Organization', backref=db.backref('vendors', lazy=True))


class LineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # Establish relationship with Product
    product = db.relationship('Product', backref=db.backref('line_items', lazy=True))


class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    vendor = db.relationship('Vendor', backref=db.backref('purchase_orders', lazy=True))
    line_items = db.relationship('LineItem', backref='purchase_order', lazy=True, cascade="all, delete-orphan")

# Define the Bill model
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    bill_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)

    # Relationship with PurchaseOrder
    purchase_order = db.relationship('PurchaseOrder', backref=db.backref('bills', lazy=True))

    # The relationship with BillLineItem is established through the backref in BillLineItem


# Add this code to your `models.py` or where your models are defined

# models.py

class Quote(db.Model):
    __tablename__ = 'quote'
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(50), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    quote_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Draft')

    # New field to link Quote to SetupOrganization
    organization_id = db.Column(db.Integer, db.ForeignKey('setup_organization.id'), nullable=False)

    # Relationships with Customer and Organization
    customer = db.relationship('Customer', backref=db.backref('quotes', lazy=True))
    organization = db.relationship('SetupOrganization', backref=db.backref('quotes', lazy=True))

    # Updated relationship to QuoteLineItem with a unique backref name
    line_items = db.relationship('QuoteLineItem', backref='quote_ref', lazy=True, cascade="all, delete-orphan")


class QuoteLineItem(db.Model):
    __tablename__ = 'quote_line_item'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # Updated relationship to Quote with a unique backref name
    quote = db.relationship('Quote', backref=db.backref('quote_line_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('quote_line_items', lazy=True))

class BillLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # Relationship to link to the Bill
    bill = db.relationship('Bill', backref=db.backref('bill_line_items', lazy=True))



    # Use a unique relationship name without using 'bill' to avoid conflict
    # No need to define a backref here, as the Bill model already has one


# app.py or models.py

# SalesOrder Model
class SalesOrder(db.Model):
    __tablename__ = 'sales_order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Draft')

    # New field to link SalesOrder to SetupOrganization
    organization_id = db.Column(db.Integer, db.ForeignKey('setup_organization.id'), nullable=False)

    # New field to link SalesOrder to Quote
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'),
                         nullable=True)  # Nullable if not all Sales Orders are created from Quotes

    # Relationship with Customer, Organization, and Quote
    customer = db.relationship('Customer', backref=db.backref('sales_orders', lazy=True))
    organization = db.relationship('SetupOrganization', backref=db.backref('sales_orders', lazy=True))
    quote = db.relationship('Quote', backref=db.backref('sales_orders', lazy=True))  # Establish relationship with Quote

    # Use a unique backref name to avoid conflict with the SalesOrderLineItem relationship
    line_items = db.relationship('SalesOrderLineItem', backref='order_ref', lazy=True, cascade="all, delete-orphan")


# SalesOrderLineItem Model
class SalesOrderLineItem(db.Model):
    __tablename__ = 'sales_order_line_item'
    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)  # Add product_id as FK
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # Relationship to Product using a unique backref name
    product = db.relationship('Product', backref=db.backref('sales_order_line_items', lazy=True))

    # Relationship to SalesOrder using a unique backref name
    sales_order = db.relationship('SalesOrder', backref=db.backref('sales_order_line_items', lazy=True))


# app.py (or models.py)

class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Draft')

    # Foreign key to link the invoice to an organization
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    # Relationship with Customer and Line Items
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))
    line_items = db.relationship('InvoiceLineItem', backref='invoice_ref', lazy=True, cascade="all, delete-orphan")

class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_item'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)  # Add product_id as FK
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    # Relationship to Invoice
    invoice = db.relationship('Invoice', backref=db.backref('invoice_line_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('invoice_line_items', lazy=True))

# app.py or models.py

class Shipment(db.Model):
    __tablename__ = 'shipment'
    id = db.Column(db.Integer, primary_key=True)
    shipment_number = db.Column(db.String(50), nullable=False, unique=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    shipment_date = db.Column(db.Date, nullable=False)
    carrier = db.Column(db.String(100), nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pending')  # Status of the shipment
    stage = db.Column(db.String(50), nullable=False, default='Pending')  # Shipment stages
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    # Relationships
    invoice = db.relationship('Invoice', backref=db.backref('shipments', lazy=True))
    organization = db.relationship('Organization', backref=db.backref('shipments', lazy=True))


# Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['userId']
        password = request.form['password']

        # Fetch user by username
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['organization_id'] = user.organization_id  # Store organization ID in session
            flash('Logged in successfully!', 'success')
            return redirect(url_for('vendor_list'))
        else:
            flash("Invalid username or password. Please try again.", 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', show_logo=False)

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('organization_id', None)  # Remove organization ID from session on logout
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Login Required Decorator
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
    wrap.__name__ = f.__name__
    return wrap


# Setup Organization Page (Used for Initial Setup)
@app.route('/setup_organization', methods=['GET', 'POST'])
@login_required
def setup_organization():
    if request.method == 'POST':
        org_name = request.form['org_name']
        gst_number = request.form['gst_number']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']
        # contact_person = request.form['contact_person']
        org_type = request.form['org_type']

        # Create a new organization for setup
        new_org = SetupOrganization(
            org_name=org_name,
            gst_number=gst_number,
            email_id=email_id,
            phone_number=phone_number,
            address=address,
            # contact_person=contact_person,
            org_type=org_type
        )
        db.session.add(new_org)
        db.session.commit()

        # Set the setup organization_id in session
        session['organization_id'] = new_org.id

        flash('Organization setup successfully!', 'success')
        return redirect(url_for('add_users'))

    return render_template('setup_organization.html', show_logo=False, show_navbar=False)


# Add Users Page
@app.route('/add_users', methods=['GET', 'POST'])
@login_required
def add_users():
    if request.method == 'POST':
        usernames = request.form.getlist('username[]')
        passwords = request.form.getlist('password[]')
        roles = request.form.getlist('role[]')

        # Retrieve organization_id from session
        organization_id = session.get('organization_id')

        # Check if there is at least one Admin in the form submission
        has_admin = any(role == 'Admin' for role in roles)

        # Check if the organization already has an Admin user
        existing_admin = User.query.filter_by(organization_id=organization_id, role='Admin').first()

        # If no Admin in the form and no existing Admin in the organization, prevent submission
        if not has_admin and not existing_admin:
            # Instead of just flashing, use a special key for showing a pop-up
            flash("Minimum 1 Admin required.", 'admin_required')
            return redirect(url_for('add_users'))

        for username, password, role in zip(usernames, passwords, roles):
            # Check if the username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash(f"Username '{username}' already exists. Please choose a different username.", 'danger')
                return redirect(url_for('add_users'))

            # If username is unique, create a new user
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password, role=role, organization_id=organization_id)
            db.session.add(new_user)

        db.session.commit()
        flash('Users added successfully!', 'success')
        return redirect(url_for('vendor_list'))

    return render_template('add_users.html', show_logo=True, show_navbar=False)



@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)

    # Check if the user to be deleted is the only Admin in the organization
    existing_admins = User.query.filter_by(organization_id=user_to_delete.organization_id, role='Admin').all()

    if len(existing_admins) == 1 and user_to_delete.role == 'Admin':
        flash("You cannot delete the only Admin user in the organization.", "danger")
        return redirect(url_for('user_list'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for('user_list'))


@app.route('/organization_master', methods=['GET', 'POST'])
@login_required
def organization_master():
    # Check if request is POST (form submission)
    if request.method == 'POST':
        org_name = request.form['org_name']
        gst_number = request.form['gst_number']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']
        # contact_person = request.form['contact_person']
        org_type = request.form['org_type']
        business_type = request.form['business_type']

        # Create a new organization entry
        new_organization = Organization(
            org_name=org_name,
            gst_number=gst_number,
            email_id=email_id,
            phone_number=phone_number,
            address=address,
            # contact_person=contact_person,
            org_type=org_type,
            business_type=business_type
        )
        db.session.add(new_organization)
        db.session.commit()  # Commit the new organization to the database

        # Redirect to organization list page after successful submission
        flash('Organization added successfully!', 'success')
        return redirect(url_for('organization_list'))

    return render_template('organization_master.html', show_logo=True, active_tab='organization')

# Product List Page
@app.route('/product_list')
@login_required
def product_list():
    # Retrieve the organization_id from the session
    organization_id = session.get('organization_id')
    if not organization_id:
        flash('Organization not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    # Fetch only products related to the logged-in user's organization
    products = Product.query.filter_by(organization_id=organization_id).all()
    return render_template('product_list.html', products=products, show_logo=True, active_tab='product')

# app.py

# Customer List Page
@app.route('/customer_list')
@login_required
def customer_list():
    # Retrieve the organization ID from the session
    organization_id = session.get('organization_id')

    # Fetch only customers that belong to the user's organization
    customers = Customer.query.filter_by(organization_id=organization_id).all()

    return render_template('customer_list.html', customers=customers, show_logo=True, active_tab='customer')
# Add New Customer Page and Form Submission
@app.route('/customer_master', methods=['GET', 'POST'])
@login_required
def customer_master():
    if request.method == 'POST':
        # Retrieve form data
        customer_name = request.form['customer_name']
        company_name = request.form['company_name']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']
        gst_number = request.form['gst_number']

        # Check if organization_id exists in session
        organization_id = session.get('organization_id')
        if not organization_id:
            flash('Organization not found. Please log in again.', 'danger')
            return redirect(url_for('login'))

        # Create a new customer with the organization ID
        new_customer = Customer(
            customer_name=customer_name,
            company_name=company_name,
            email_id=email_id,
            phone_number=phone_number,
            address=address,
            gst_number=gst_number,
            organization_id=organization_id  # Link to the organization
        )
        db.session.add(new_customer)
        db.session.commit()

        flash('Customer added successfully!', 'success')
        return redirect(url_for('customer_list'))

    return render_template('customer_master.html', show_logo=True, active_tab='customer_master')


# Edit Customer Route
@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    # Retrieve the organization ID from the session
    organization_id = session.get('organization_id')

    # Ensure the customer belongs to the user's organization
    customer = Customer.query.filter_by(id=customer_id, organization_id=organization_id).first_or_404()

    if request.method == 'POST':
        # Update customer details
        customer.customer_name = request.form['customer_name']
        customer.company_name = request.form['company_name']
        customer.email_id = request.form['email_id']
        customer.phone_number = request.form['phone_number']
        customer.address = request.form['address']
        customer.gst_number = request.form['gst_number']

        # Save the changes to the database
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customer_list'))

    return render_template('edit_customer.html', customer=customer, show_logo=True, active_tab='customer')


# Delete Customer Route
@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    # Retrieve the organization ID from the session
    organization_id = session.get('organization_id')

    # Ensure the customer belongs to the user's organization
    customer = Customer.query.filter_by(id=customer_id, organization_id=organization_id).first_or_404()

    try:
        # Delete the customer
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash(f'An error occurred while deleting the customer: {str(e)}', 'danger')

    return redirect(url_for('customer_list'))



# Add New Product Page and Form Submission
# Add New Product Page and Form Submission
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        description = request.form.get('description')
        product_code = request.form.get('product_code')
        sku = request.form.get('sku')
        product_type = request.form.get('product_type')
        category = request.form.get('category')
        unit = request.form.get('unit')
        unit_price = float(request.form.get('unit_price', 0))
        cost_price = float(request.form.get('cost_price', 0))
        quantity_in_stock = int(request.form.get('quantity_in_stock', 0))
        reorder_level = int(request.form.get('reorder_level', 0))
        gst_rate = float(request.form.get('gst_rate', 0))
        hsn_code = request.form.get('hsn_code')
        supplier = request.form.get('supplier')
        status = request.form.get('status', 'Active')
        brand = request.form.get('brand')

        # Retrieve the organization_id from the session
        organization_id = session.get('organization_id')
        if not organization_id:
            flash('Organization not found. Please log in again.', 'danger')
            return redirect(url_for('login'))

        # Create a new product object
        new_product = Product(
            product_name=product_name,
            description=description,
            product_code=product_code,
            sku=sku,
            product_type=product_type,
            category=category,
            unit=unit,
            unit_price=unit_price,
            cost_price=cost_price,
            quantity_in_stock=quantity_in_stock,
            reorder_level=reorder_level,
            gst_rate=gst_rate,
            hsn_code=hsn_code,
            supplier=supplier,
            status=status,
            brand=brand,
            organization_id=organization_id  # Link the product to the organization
        )

        try:
            # Attempt to add the new product to the database
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('product_list'))
        except IntegrityError:
            db.session.rollback()  # Rollback the session to handle the error
            flash('A product with the same product code already exists. Please use a different product code.', 'danger')
            return redirect(url_for('add_product'))

    return render_template('add_product.html', show_logo=True, active_tab='products')

# Edit Product Page and Form Submission
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    # Fetch the product to be edited
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        # Print the form data to debug missing keys
        print(request.form)

        # Update product details from the form submission
        product.product_name = request.form['product_name']
        product.description = request.form['description']
        product.product_code = request.form['product_code']
        product.unit = request.form['unit']
        product.category = request.form['category']
        product.product_type = request.form['product_type']
        product.brand = request.form['brand']  # Ensure this field exists in the form
        product.unit_price = float(request.form['unit_price'])
        product.cost_price = float(request.form['cost_price']) if request.form['cost_price'] else None
        product.quantity_in_stock = int(request.form['quantity_in_stock'])
        product.reorder_level = int(request.form['reorder_level']) if request.form['reorder_level'] else None
        product.gst_rate = float(request.form['gst_rate']) if request.form['gst_rate'] else None
        product.hsn_code = request.form['hsn_code']
        product.supplier = request.form['supplier']
        product.status = request.form['status']

        # Save the updated product to the database
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_list'))

    return render_template('edit_product.html', product=product, show_logo=True, active_tab='product')



# Delete Product Route
@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    # Fetch the product to be deleted
    product = Product.query.get_or_404(product_id)

    try:
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash(f'An error occurred while deleting the product: {str(e)}', 'danger')

    return redirect(url_for('product_list'))


@app.route('/organization_list')
@login_required
def organization_list():
    # Fetch only organizations related to the logged-in user's organization
    organization_id = session.get('organization_id')
    organizations = Organization.query.filter_by(id=organization_id).all()  # Replace with appropriate filtering logic

    # Print statement to ensure organizations are being fetched correctly
    print("Organizations fetched:", organizations)

    return render_template('organization_list.html', organizations=organizations, show_logo=True,
                           active_tab='organization')


# Edit Organization Route
@app.route('/edit_organization/<int:organization_id>', methods=['GET', 'POST'])
@login_required
def edit_organization(organization_id):
    # Retrieve the organization using the provided ID
    organization = Organization.query.get_or_404(organization_id)

    if request.method == 'POST':
        # Update organization details with form data
        organization.org_name = request.form['org_name']
        organization.org_type = request.form['org_type']
        organization.email_id = request.form['email_id']
        organization.phone_number = request.form['phone_number']
        organization.address = request.form['address']

        # Retrieve business type and GST number
        business_type = request.form['business_type']
        organization.business_type = business_type

        # If the business type is "GST Registered," set the GST number
        if business_type == "GST Registered":
            organization.gst_number = request.form['gst_number']
        else:
            organization.gst_number = None  # Clear the GST number for other business types

        # Save the changes to the database
        db.session.commit()
        flash('Organization updated successfully!', 'success')
        return redirect(url_for('organization_list'))

    # Render edit organization form with the current organization details
    return render_template('organization_master.html', organization=organization, show_logo=True,
                           active_tab='organization')


# Delete Organization
@app.route('/delete_organization/<int:organization_id>', methods=['POST'])
@login_required
def delete_organization(organization_id):
    organization = Organization.query.get_or_404(organization_id)

    try:
        # Delete the organization
        db.session.delete(organization)
        db.session.commit()
        flash('Organization deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash(f'An error occurred while deleting the organization: {str(e)}', 'danger')

    return redirect(url_for('organization_list'))


# Vendor List Page
@app.route('/vendor_list')
@login_required
def vendor_list():
    # Fetch only vendors related to the logged-in user's organization
    organization_id = session.get('organization_id')
    vendors = Vendor.query.filter_by(organization_id=organization_id).all()
    return render_template('vendor_list.html', vendors=vendors, show_logo=True, active_tab='vendor_list')


# Bill List Page
@app.route('/bill_list')
@login_required
def bill_list():
    organization_id = session.get('organization_id')
    bills = Bill.query.join(PurchaseOrder).join(Vendor).filter(Vendor.organization_id == organization_id).all()
    return render_template('bill_list.html', bills=bills, show_logo=True, active_tab='bill_list')


@app.route('/bill')
@login_required
def bill():
    # Retrieve the organization ID from the session to filter bills for the logged-in user's organization
    organization_id = session.get('organization_id')

    # Query the bills associated with this organization
    bills = Bill.query.join(PurchaseOrder).join(Vendor).filter(Vendor.organization_id == organization_id).all()

    # Render the bill_list template with the bills data
    return render_template('bill_list.html', bills=bills, show_logo=True, active_tab='bill_list')


# app.py

# Updated Create Bill Function to Update Purchase Order Status
@app.route('/create_bill', methods=['GET', 'POST'])
@login_required
def create_bill():
    if request.method == 'POST':
        bill_number = request.form['bill_number']
        purchase_order_id = request.form['purchase_order_id']
        bill_date = datetime.strptime(request.form['bill_date'], '%Y-%m-%d')
        total_amount = request.form['total_amount']
        status = request.form['status']

        # Create the Bill
        new_bill = Bill(
            bill_number=bill_number,
            purchase_order_id=purchase_order_id,
            bill_date=bill_date,
            total_amount=total_amount,
            status=status
        )
        db.session.add(new_bill)
        db.session.commit()

        # Mark the selected Purchase Order as 'Billed'
        purchase_order = PurchaseOrder.query.get(purchase_order_id)
        purchase_order.status = 'Billed'
        db.session.commit()

        # Add line items to the Bill
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            new_line_item = BillLineItem(
                bill_id=new_bill.id,
                item_name=item_name,
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Bill created successfully!', 'success')
        return redirect(url_for('bill_list'))

    # Only show purchase orders that are not billed
    purchase_orders = PurchaseOrder.query.filter(PurchaseOrder.status != 'Billed').all()
    return render_template('create_bill.html', purchase_orders=purchase_orders)

# Edit Bill Route
@app.route('/edit_bill/<int:bill_id>', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    # Retrieve the bill from the database using the provided bill ID
    bill = Bill.query.get_or_404(bill_id)

    # Fetch the associated line items for this bill
    line_items = BillLineItem.query.filter_by(bill_id=bill_id).all()

    # Fetch the purchase orders associated with the organization
    organization_id = session.get('organization_id')
    purchase_orders = PurchaseOrder.query.join(Vendor).filter(Vendor.organization_id == organization_id).all()

    if request.method == 'POST':
        # Update the bill details
        bill.bill_number = request.form['bill_number']
        bill.purchase_order_id = request.form['purchase_order_id']
        bill.bill_date = datetime.strptime(request.form['bill_date'], '%Y-%m-%d')
        bill.total_amount = float(request.form['total_amount'])
        bill.status = request.form['status']

        # Delete existing line items for the bill to update them
        BillLineItem.query.filter_by(bill_id=bill_id).delete()

        # Add updated line items
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
            new_line_item = BillLineItem(
                bill_id=bill.id,
                item_name=Product.query.get(int(product_id)).product_name,  # Get the product name from Product table
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        # Save the updated bill details
        db.session.commit()
        flash('Bill updated successfully!', 'success')
        return redirect(url_for('bill_list'))

    # Render the edit_bill.html template with the bill and its line items
    products = Product.query.filter_by(organization_id=organization_id).all()
    return render_template('edit_bill.html', bill=bill, line_items=line_items, purchase_orders=purchase_orders, products=products, show_logo=True, active_tab='bill')



# Delete Bill
@app.route('/delete_bill/<int:bill_id>', methods=['POST'])
@login_required
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    try:
        db.session.delete(bill)
        db.session.commit()
        flash('Bill deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the bill: {str(e)}', 'danger')

    return redirect(url_for('bill_list'))

# Purchase Order List with "Create Bill" Option
@app.route('/purchase_order_list')
@login_required
def purchase_order_list():
    organization_id = session.get('organization_id')
    purchase_orders = PurchaseOrder.query.join(Vendor).filter(Vendor.organization_id == organization_id).all()
    return render_template('purchase_order_list.html', purchase_orders=purchase_orders, show_logo=True, active_tab='purchase_order')
# Add New Purchase Order (Purchase Order Form)
# Add New Purchase Order (Purchase Order Form)
@app.route('/purchase_order', methods=['GET', 'POST'])
@login_required
def purchase_order():
    if request.method == 'POST':
        vendor_id = request.form['vendor_id']
        order_date = request.form['order_date']
        total_amount = request.form['total_amount']
        status = request.form['status']

        # Create new purchase order
        new_order = PurchaseOrder(
            vendor_id=vendor_id,
            order_date=datetime.strptime(order_date, '%Y-%m-%d'),
            total_amount=total_amount,
            status=status
        )
        db.session.add(new_order)
        db.session.commit()

        # Add line items using product lookup
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
            product = Product.query.get(product_id)
            new_line_item = LineItem(
                purchase_order_id=new_order.id,
                product_id=product_id,
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Purchase Order created successfully!', 'success')
        return redirect(url_for('purchase_order_list'))

    vendors = Vendor.query.all()  # Get the list of vendors for the dropdown
    products = Product.query.all()  # Fetch all products for the dropdown
    return render_template('purchase_order.html', vendors=vendors, products=products, show_logo=True, active_tab='purchase_order')



# Edit Purchase Order
@app.route('/edit_purchase_order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_purchase_order(order_id):
    # Retrieve the purchase order to be edited
    order = PurchaseOrder.query.get_or_404(order_id)

    if request.method == 'POST':
        # Update the purchase order with new data
        order.vendor_id = request.form['vendor_id']

        # Convert the order date to a Python date object
        order_date_str = request.form['order_date']
        try:
            order.order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use 'YYYY-MM-DD'.", 'danger')
            return redirect(url_for('edit_purchase_order', order_id=order_id))

        order.total_amount = float(request.form['total_amount'])
        order.status = request.form['status']

        # Update or add line items
        item_ids = request.form.getlist('item_id[]')  # Existing line item IDs
        product_ids = request.form.getlist('product_id[]')  # Product IDs selected from the dropdown
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        # Create a set of existing item IDs for tracking deletions
        existing_item_ids = set(int(item.id) for item in order.line_items)

        # Loop through the form data to update or add line items
        for i, item_id in enumerate(item_ids):
            if item_id:  # Update existing line item
                line_item = LineItem.query.get(int(item_id))
                line_item.product_id = int(product_ids[i])  # Update product_id
                line_item.quantity = int(quantities[i])
                line_item.unit_price = float(unit_prices[i])
                existing_item_ids.remove(int(item_id))  # Remove from existing set
            else:  # Add new line item
                new_line_item = LineItem(
                    purchase_order_id=order.id,
                    product_id=int(product_ids[i]),  # Assign product_id
                    quantity=int(quantities[i]),
                    unit_price=float(unit_prices[i])
                )
                db.session.add(new_line_item)

        # Delete line items that were removed
        for item_id in existing_item_ids:
            line_item_to_delete = LineItem.query.get(item_id)
            db.session.delete(line_item_to_delete)

        # Commit changes to the database
        db.session.commit()
        flash('Purchase Order updated successfully!', 'success')
        return redirect(url_for('purchase_order_list'))

    # If the request method is GET, show the form to edit the order
    vendors = Vendor.query.all()
    products = Product.query.filter_by(organization_id=session.get('organization_id')).all()  # Fetch products for the organization
    line_items = LineItem.query.filter_by(purchase_order_id=order_id).all()

    return render_template('edit_purchase_order.html', order=order, vendors=vendors, products=products, line_items=line_items,
                           show_logo=True, active_tab='purchase_order')



@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    # Retrieve the status from the form submission
    new_status = request.form.get('status')

    # Find the purchase order by ID
    order = PurchaseOrder.query.get_or_404(order_id)

    # Check if the new status is valid and update it
    if new_status in ['Pending', 'Completed', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Order {order_id} status updated to {new_status} successfully!', 'success')
    else:
        flash('Invalid status value.', 'danger')

    return redirect(url_for('purchase_order_list'))

# Delete Purchase Order
@app.route('/delete_purchase_order/<int:order_id>', methods=['POST'])
@login_required
def delete_purchase_order(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()

    flash('Purchase Order deleted successfully!', 'success')
    return redirect(url_for('purchase_order_list'))


# Add New Vendor (Vendor Master Form)
@app.route('/vendor_master', methods=['GET', 'POST'])
@login_required
def vendor_master():
    if request.method == 'POST':
        # Retrieve form data
        vendor_name = request.form['vendor_name']
        company_name = request.form['company_name']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']

        # Check if organization_id exists in session
        organization_id = session.get('organization_id')
        if not organization_id:
            flash('Organization not found. Please log in again.', 'danger')
            return redirect(url_for('login'))

        # Create a new vendor with the organization ID
        new_vendor = Vendor(
            vendor_name=vendor_name,
            company_name=company_name,
            email_id=email_id,
            phone_number=phone_number,
            address=address,
            organization_id=organization_id  # Link to the organization
        )
        db.session.add(new_vendor)
        db.session.commit()

        flash('Vendor added successfully!', 'success')
        return redirect(url_for('vendor_list'))

    return render_template('vendor_master.html', show_logo=True, active_tab='vendor_master')

# Route to get purchase order line items for dynamic fetching
@app.route('/get_purchase_order_items/<int:purchase_order_id>', methods=['GET'])
@login_required
def get_purchase_order_items(purchase_order_id):
    # Fetch line items for the specified purchase order
    line_items = LineItem.query.filter_by(purchase_order_id=purchase_order_id).all()
    line_item_data = [
        {
            'item_name': item.product.product_name,  # Get product name from relationship
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'total': item.quantity * item.unit_price
        }
        for item in line_items
    ]
    return jsonify({'line_items': line_item_data})

# Edit Vendor
@app.route('/edit_vendor/<int:vendor_id>', methods=['GET', 'POST'])
@login_required
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)

    if request.method == 'POST':
        # Update the vendor details
        vendor.vendor_name = request.form['vendor_name']
        vendor.company_name = request.form['company_name']
        vendor.email_id = request.form['email_id']
        vendor.phone_number = request.form['phone_number']
        vendor.address = request.form['address']

        # Save the changes to the database
        db.session.commit()
        flash('Vendor updated successfully!', 'success')
        return redirect(url_for('vendor_list'))

    # Render the edit form pre-filled with vendor details
    return render_template('edit_vendor.html', vendor=vendor, show_logo=True, active_tab='vendor_master')


@app.route('/delete_vendor/<int:vendor_id>', methods=['POST'])
@login_required
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)

    try:
        # Delete the vendor
        db.session.delete(vendor)
        db.session.commit()
        flash('Vendor deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash(f'An error occurred while deleting the vendor: {str(e)}', 'danger')

    return redirect(url_for('vendor_list'))

# Quote List Page
# Example route for displaying quotes with organization filtering
@app.route('/quote')
@login_required
def quote_list():
    organization_id = session.get('organization_id')

    # Get all quotes belonging to the user's organization
    quotes = Quote.query.filter(Quote.organization_id == organization_id).all()

    # Create a dictionary to store if a sales order exists for each quote
    quotes_with_sales_order = {}
    for quote in quotes:
        # Disable actions for quotes that are converted to sales order
        quotes_with_sales_order[quote.id] = quote.status == 'Converted to Sales Order'

    return render_template('quote_list.html', quotes=quotes, quotes_with_sales_order=quotes_with_sales_order, show_logo=True, active_tab='quote')





@app.route('/create_quote', methods=['GET', 'POST'])
@login_required
def create_quote():
    if request.method == 'POST':
        # Auto-generate a unique quote number
        last_quote = Quote.query.order_by(Quote.id.desc()).first()
        if last_quote:
            new_quote_number = str(int(last_quote.quote_number) + 1)
        else:
            new_quote_number = "1"  # Start with '1' if there are no quotes in the system

        customer_id = request.form['customer_id']
        quote_date = datetime.strptime(request.form['quote_date'], '%Y-%m-%d')
        total_amount = float(request.form['total_amount'])
        status = request.form['status']

        # Get the organization ID from session (assuming you have organization-specific quotes)
        organization_id = session.get('organization_id')

        # Create a new Quote object with the auto-generated quote number and organization_id
        new_quote = Quote(
            quote_number=new_quote_number,
            customer_id=customer_id,
            quote_date=quote_date,
            total_amount=total_amount,
            status=status,
            organization_id=organization_id  # Assign the organization ID if applicable
        )
        db.session.add(new_quote)
        db.session.commit()

        # Add line items to the Quote
        product_ids = request.form.getlist('product_id[]')  # Get product IDs instead of names
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
            # Create a new line item using product_id, quantity, and unit_price
            new_line_item = QuoteLineItem(
                quote_id=new_quote.id,
                product_id=int(product_id),  # Use product_id to link with the product
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Quote created successfully!', 'success')
        return redirect(url_for('quote_list'))

    # Fetch customers and products for dropdown lists
    customers = Customer.query.filter_by(organization_id=session['organization_id']).all()
    products = Product.query.filter_by(organization_id=session['organization_id']).all()  # Fetch products for the current organization
    return render_template('create_quote.html', customers=customers, products=products, show_logo=True, active_tab='quote')



# Example route to edit a quote with organization filtering
@app.route('/edit_quote/<int:quote_id>', methods=['GET', 'POST'])
@login_required
def edit_quote(quote_id):
    # Fetch the organization ID from the session
    organization_id = session.get('organization_id')

    # Query to get the quote only if it belongs to the user's organization
    quote = Quote.query.join(Customer).filter(
        Quote.id == quote_id,
        Customer.organization_id == organization_id  # Ensure the quote belongs to the current organization
    ).first_or_404()

    # Fetch customers belonging to the user's organization
    customers = Customer.query.filter_by(organization_id=organization_id).all()

    # Fetch products to populate the dropdown for line items
    products = Product.query.filter_by(organization_id=organization_id).all()

    if request.method == 'POST':
        # Update quote details from the form submission
        quote.customer_id = request.form['customer_id']
        quote.quote_date = datetime.strptime(request.form['quote_date'], '%Y-%m-%d')
        quote.total_amount = float(request.form['total_amount'])
        quote.status = request.form['status']

        # Remove existing line items
        QuoteLineItem.query.filter_by(quote_id=quote_id).delete()

        # Add new line items from the form data
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
            # Ensure product_id is valid and not empty
            if product_id:
                new_line_item = QuoteLineItem(
                    quote_id=quote.id,
                    product_id=int(product_id),
                    quantity=int(quantity),
                    unit_price=float(unit_price)
                )
                db.session.add(new_line_item)

        db.session.commit()
        flash('Quote updated successfully!', 'success')
        return redirect(url_for('quote_list'))

    return render_template('edit_quote.html', quote=quote, customers=customers, products=products, show_logo=True, active_tab='quote')



# Delete Quote
@app.route('/delete_quote/<int:quote_id>', methods=['POST'])
@login_required
def delete_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    flash('Quote deleted successfully!', 'success')
    return redirect(url_for('quote_list'))

# Sales Order List Page
# Sales Order List Page with Organization Filtering
@app.route('/sales_order', methods=['GET'])
@login_required
def sales_order_list():
    organization_id = session.get('organization_id')

    # Query to filter sales orders by organization
    sales_orders = SalesOrder.query.join(Customer).filter(
        Customer.organization_id == organization_id,
        SalesOrder.organization_id == organization_id  # Ensure sales order belongs to the user's organization
    ).all()

    return render_template('sales_order_list.html', sales_orders=sales_orders, show_logo=True, active_tab='sales_order')


# @app.route('/get_quote_details/<int:quote_id>', methods=['GET'])
# @login_required
# def get_quote_details(quote_id):
#     # Retrieve the quote and associated line items
#     quote = Quote.query.get_or_404(quote_id)
#     customer = quote.customer
#     line_items = quote.line_items
#
#     # Prepare data to return as JSON
#     data = {
#         'customer_name': customer.customer_name,
#         'customer_id': customer.id,
#         'line_items': [{'item_name': item.item_name, 'quantity': item.quantity, 'unit_price': item.unit_price} for item in line_items],
#         'total_amount': quote.total_amount
#     }
#     return jsonify(data)

# Route to create a sales order
@app.route('/create_sales_order', methods=['GET', 'POST'])
@login_required
def create_sales_order():
    organization_id = session.get('organization_id')
    approved_quotes = Quote.query.filter_by(status='Approved', organization_id=organization_id).all()
    customers = Customer.query.filter_by(organization_id=organization_id).all()
    products = Product.query.filter_by(organization_id=organization_id).all()

    if request.method == 'POST':
        try:
            order_number = request.form['order_number']
            customer_id = request.form['customer_id']
            order_date = datetime.strptime(request.form['order_date'], '%Y-%m-%d')
            total_amount = float(request.form['total_amount'])
            status = request.form['status']
            quote_id = request.form['quote_id']  # Capture the quote ID used for creating this sales order

            # Create a new SalesOrder object
            new_sales_order = SalesOrder(
                order_number=order_number,
                customer_id=customer_id,
                order_date=order_date,
                total_amount=total_amount,
                status=status,
                organization_id=organization_id,
                quote_id=quote_id  # Link the quote ID to the sales order
            )
            db.session.add(new_sales_order)
            db.session.commit()  # Commit the sales order first to get its ID

            # Add line items to the SalesOrder
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')

            for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
                new_line_item = SalesOrderLineItem(
                    sales_order_id=new_sales_order.id,  # Use the newly created sales order's ID
                    product_id=int(product_id),
                    quantity=int(quantity),
                    unit_price=float(unit_price)
                )
                db.session.add(new_line_item)

            # Update the quote status to 'Converted to Sales Order'
            quote = Quote.query.get(quote_id)
            if quote:
                quote.status = 'Converted to Sales Order'
                db.session.add(quote)  # Add the updated quote to the session

            db.session.commit()  # Commit both the new sales order line items and quote status update
            flash('Sales order created successfully and quote status updated!', 'success')
            return redirect(url_for('sales_order_list'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to create sales order: {e}")
            flash('Failed to create sales order. Please try again.', 'danger')

    return render_template('create_sales_order.html', approved_quotes=approved_quotes, customers=customers, products=products, show_logo=True, active_tab='sales_order')


# Route to get quote details for populating sales order fields
@app.route('/get_quote_details/<int:quote_id>', methods=['GET'])
@login_required
def get_quote_details(quote_id):
    # Fetch the quote details based on the quote_id
    organization_id = session.get('organization_id')
    quote = Quote.query.filter_by(id=quote_id, organization_id=organization_id, status='Approved').first_or_404()

    # Retrieve line items for the quote
    line_items = [
        {
            'product_id': line_item.product_id,
            'product_name': line_item.product.product_name,
            'quantity': line_item.quantity,
            'unit_price': line_item.unit_price
        }
        for line_item in quote.line_items
    ]

    # Prepare data to return as JSON
    quote_details = {
        'quote_number': quote.quote_number,
        'customer_id': quote.customer_id,
        'quote_date': quote.quote_date.strftime('%Y-%m-%d'),
        'total_amount': quote.total_amount,
        'line_items': line_items
    }

    return jsonify(quote_details)



# Edit Sales Order Route
@app.route('/edit_sales_order/<int:sales_order_id>', methods=['GET', 'POST'])
@login_required
def edit_sales_order(sales_order_id):
    # Retrieve the sales order using the provided ID and ensure it belongs to the current organization
    organization_id = session.get('organization_id')
    sales_order = SalesOrder.query.filter_by(id=sales_order_id, organization_id=organization_id).first_or_404()

    # Fetch the associated line items for this sales order
    line_items = SalesOrderLineItem.query.filter_by(sales_order_id=sales_order_id).all()

    # Debug: Print the retrieved line items to confirm they are being fetched
    print("Line Items Retrieved: ", line_items)

    # If the request method is POST, update the sales order details
    if request.method == 'POST':
        # Update the sales order details from form data
        sales_order.order_number = request.form['order_number']
        sales_order.customer_id = request.form['customer_id']
        sales_order.order_date = datetime.strptime(request.form['order_date'], '%Y-%m-%d')
        sales_order.total_amount = float(request.form['total_amount'])
        sales_order.status = request.form['status']

        # Remove existing line items to update them
        SalesOrderLineItem.query.filter_by(sales_order_id=sales_order_id).delete()

        # Add updated line items
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for product_id, quantity, unit_price in zip(product_ids, quantities, unit_prices):
            new_line_item = SalesOrderLineItem(
                sales_order_id=sales_order_id,
                product_id=int(product_id),
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        # Commit the updated sales order and its line items
        db.session.commit()
        flash('Sales Order updated successfully!', 'success')
        return redirect(url_for('sales_order_list'))

    # Fetch all customers and products for the dropdowns
    customers = Customer.query.filter_by(organization_id=organization_id).all()
    products = Product.query.filter_by(organization_id=organization_id).all()  # Get products for organization

    # Render the edit_sales_order template with the sales order and its line items
    return render_template(
        'edit_sales_order.html',
        sales_order=sales_order,
        line_items=line_items,
        customers=customers,
        products=products,
        show_logo=True,
        active_tab='sales_order'
    )

# Delete Sales Order
@app.route('/delete_sales_order/<int:order_id>', methods=['POST'])
@login_required
def delete_sales_order(order_id):
    # Ensure the sales order belongs to the user's organization before deletion
    organization_id = session.get('organization_id')
    sales_order = SalesOrder.query.join(Customer).filter(
        SalesOrder.id == order_id,
        Customer.organization_id == organization_id,
        SalesOrder.organization_id == organization_id
    ).first_or_404()

    # Check if the sales order is associated with a quote
    if sales_order.quote_id:
        # Retrieve the associated quote and update its status to 'Draft'
        quote = Quote.query.get(sales_order.quote_id)
        if quote:
            quote.status = 'Draft'
            db.session.add(quote)

    # Delete the sales order
    db.session.delete(sales_order)
    db.session.commit()
    flash('Sales Order deleted successfully and quote status updated to Draft!', 'success')
    return redirect(url_for('sales_order_list'))

# app.py

@app.route('/invoice', methods=['GET', 'POST'])
@login_required
def invoice_list():
    # Retrieve organization ID from session
    organization_id = session.get('organization_id')
    invoices = Invoice.query.join(Customer).filter(
        Customer.organization_id == organization_id,
        Invoice.organization_id == organization_id
    ).all()
    return render_template('invoice_list.html', invoices=invoices, show_logo=True, active_tab='invoice')


@app.route('/create_invoice', methods=['GET', 'POST'])
@login_required
def create_invoice():
    if request.method == 'POST':
        # Retrieve organization ID from session
        organization_id = session.get('organization_id')

        # Auto-generate a unique invoice number
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        if last_invoice:
            new_invoice_number = str(int(last_invoice.invoice_number) + 1)
        else:
            new_invoice_number = "1"  # Start with '1' if there are no invoices in the system

        customer_id = request.form['customer_id']
        invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d')
        total_amount = float(request.form['total_amount'])
        status = request.form['status']

        # Create a new Invoice object
        new_invoice = Invoice(
            invoice_number=new_invoice_number,
            customer_id=customer_id,
            invoice_date=invoice_date,
            total_amount=total_amount,
            status=status,
            organization_id=organization_id  # Link the invoice to the organization
        )
        db.session.add(new_invoice)
        db.session.commit()

        # Add line items to the Invoice
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            new_line_item = InvoiceLineItem(
                invoice_id=new_invoice.id,
                item_name=item_name,
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('invoice_list'))

    # Fetch customers belonging to the user's organization for dropdown
    organization_id = session.get('organization_id')
    customers = Customer.query.filter_by(organization_id=organization_id).all()
    return render_template('create_invoice.html', customers=customers)


@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    # Retrieve organization ID from session
    organization_id = session.get('organization_id')

    # Query to get the invoice only if it belongs to the user's organization
    invoice = Invoice.query.join(Customer).filter(
        Invoice.id == invoice_id,
        Customer.organization_id == organization_id,
        Invoice.organization_id == organization_id
    ).first_or_404()

    # Fetch customers belonging to the user's organization
    customers = Customer.query.filter_by(organization_id=organization_id).all()

    if request.method == 'POST':
        # Update invoice details from the form submission
        invoice.customer_id = request.form['customer_id']
        invoice.invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d')
        invoice.total_amount = float(request.form['total_amount'])
        invoice.status = request.form['status']

        # Remove existing line items
        InvoiceLineItem.query.filter_by(invoice_id=invoice_id).delete()

        # Add new line items from the form data
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            new_line_item = InvoiceLineItem(
                invoice_id=invoice.id,
                item_name=item_name,
                quantity=int(quantity),
                unit_price=float(unit_price)
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('invoice_list'))

    return render_template('edit_invoice.html', invoice=invoice, customers=customers, show_logo=True,
                           active_tab='invoice')


@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted successfully!', 'success')
    return redirect(url_for('invoice_list'))

@app.route('/shipment_list')
@login_required
def shipment_list():
    organization_id = session.get('organization_id')
    shipments = Shipment.query.join(Invoice).filter(
        Invoice.organization_id == organization_id,
        Shipment.organization_id == organization_id
    ).all()
    return render_template('shipment_list.html', shipments=shipments, show_logo=True, active_tab='shipment')


@app.route('/create_shipment', methods=['GET', 'POST'])
@login_required
def create_shipment():
    if request.method == 'POST':
        shipment_number = request.form['shipment_number']
        invoice_id = request.form['invoice_id']
        shipment_date = datetime.strptime(request.form['shipment_date'], '%Y-%m-%d')
        carrier = request.form['carrier']
        tracking_number = request.form['tracking_number']
        status = request.form['status']
        stage = request.form['stage']
        organization_id = session.get('organization_id')

        new_shipment = Shipment(
            shipment_number=shipment_number,
            invoice_id=invoice_id,
            shipment_date=shipment_date,
            carrier=carrier,
            tracking_number=tracking_number,
            status=status,
            stage=stage,
            organization_id=organization_id
        )
        db.session.add(new_shipment)
        db.session.commit()
        flash('Shipment created successfully!', 'success')
        return redirect(url_for('shipment_list'))

    invoices = Invoice.query.filter_by(organization_id=session.get('organization_id')).all()
    return render_template('create_shipment.html', invoices=invoices, show_logo=True, active_tab='shipment')


@app.route('/edit_shipment/<int:shipment_id>', methods=['GET', 'POST'])
@login_required
def edit_shipment(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    if request.method == 'POST':
        shipment.shipment_number = request.form['shipment_number']
        shipment.invoice_id = request.form['invoice_id']
        shipment.shipment_date = datetime.strptime(request.form['shipment_date'], '%Y-%m-%d')
        shipment.carrier = request.form['carrier']
        shipment.tracking_number = request.form['tracking_number']
        shipment.status = request.form['status']
        shipment.stage = request.form['stage']

        db.session.commit()
        flash('Shipment updated successfully!', 'success')
        return redirect(url_for('shipment_list'))

    invoices = Invoice.query.filter_by(organization_id=session.get('organization_id')).all()
    return render_template('edit_shipment.html', shipment=shipment, invoices=invoices, show_logo=True, active_tab='shipment')


@app.route('/update_shipment_status/<int:shipment_id>', methods=['POST'])
@login_required
def update_shipment_status(shipment_id):
    try:
        # Retrieve the JSON data from the request
        data = request.get_json()
        new_status = data.get('status')

        # Fetch the shipment using the provided ID
        shipment = Shipment.query.get_or_404(shipment_id)

        # Update the status of the shipment
        shipment.status = new_status

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': f'Shipment {shipment_id} status updated to {new_status} successfully!'}), 200
    except Exception as e:
        print(f"Error updating shipment status: {str(e)}")
        return jsonify({'error': 'Failed to update shipment status'}), 500


@app.route('/delete_shipment/<int:shipment_id>', methods=['POST'])
@login_required
def delete_shipment(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    db.session.delete(shipment)
    db.session.commit()
    flash('Shipment deleted successfully!', 'success')
    return redirect(url_for('shipment_list'))


@app.route('/generate_bill_pdf/<int:bill_id>', methods=['GET'])
@login_required
def generate_bill_pdf(bill_id):
    # Fetch the bill using the provided bill ID
    bill = Bill.query.get_or_404(bill_id)
    purchase_order = PurchaseOrder.query.get(bill.purchase_order_id)
    line_items = BillLineItem.query.filter_by(bill_id=bill.id).all()

    # Render the template with the bill data
    rendered = render_template('bill_pdf_template.html', bill=bill, purchase_order=purchase_order,
                               line_items=line_items)

    # Convert HTML to PDF
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(rendered.encode("UTF-8")), dest=pdf)

    # Check if PDF was successfully created
    if pisa_status.err:
        flash('Error generating PDF', 'danger')
        return redirect(url_for('bill_list'))

    # Return the generated PDF as a response
    pdf.seek(0)
    return send_file(pdf, as_attachment=True, download_name=f"Bill_{bill.bill_number}.pdf", mimetype='application/pdf')



@app.route('/generate_purchase_order_pdf/<int:order_id>', methods=['GET'])
@login_required
def generate_purchase_order_pdf(order_id):
    # Fetch the Purchase Order details based on order_id
    order = PurchaseOrder.query.get_or_404(order_id)
    line_items = LineItem.query.filter_by(purchase_order_id=order_id).all()

    # Render the template for the Purchase Order PDF
    rendered = render_template('purchase_order_pdf.html', order=order, line_items=line_items)

    # Create a PDF using WeasyPrint
    pdf = HTML(string=rendered).write_pdf()

    # Create a PDF response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=PurchaseOrder_{order.id}.pdf'

    return response

import pdfkit
from flask import send_file

@app.route('/generate_quote_pdf/<int:quote_id>', methods=['GET'])
@login_required
def generate_quote_pdf(quote_id):
    # Fetch the Quote details based on quote_id
    quote = Quote.query.get_or_404(quote_id)
    customer = Customer.query.get_or_404(quote.customer_id)
    line_items = QuoteLineItem.query.filter_by(quote_id=quote_id).all()

    # Render the template for the Quote PDF
    rendered = render_template('quote_pdf.html', quote=quote, customer=customer, line_items=line_items)

    # Create a PDF using WeasyPrint
    pdf = HTML(string=rendered).write_pdf()

    # Create a PDF response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Quote_{quote.id}.pdf'

    return response

@app.route('/generate_sales_order_pdf/<int:sales_order_id>', methods=['GET'])
@login_required
def generate_sales_order_pdf(sales_order_id):
    # Fetch the sales order using the provided ID
    organization_id = session.get('organization_id')
    sales_order = SalesOrder.query.filter_by(id=sales_order_id, organization_id=organization_id).first_or_404()

    # Fetch the associated line items for this sales order
    line_items = SalesOrderLineItem.query.filter_by(sales_order_id=sales_order_id).all()

    # Render the template with the sales order and line items data
    rendered_html = render_template('sales_order_pdf.html', sales_order=sales_order, line_items=line_items)

    # Create a PDF using WeasyPrint
    pdf = BytesIO()
    HTML(string=rendered_html).write_pdf(pdf)
    pdf.seek(0)

    # Return the generated PDF as a response
    return send_file(pdf, as_attachment=True, download_name=f"SalesOrder_{sales_order.order_number}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
