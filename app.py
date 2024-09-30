# Imports
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate  # Include Flask-Migrate for migrations
from datetime import datetime

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
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

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



# Define the BillLineItem model
class BillLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    # Define the relationship back to the Bill model with a unique backref name
    bill = db.relationship('Bill', backref=db.backref('line_items', cascade='all, delete-orphan'))


    # Use a unique relationship name without using 'bill' to avoid conflict
    # No need to define a backref here, as the Bill model already has one





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


# Route definition
# Create New Bill (Bill Form)
@app.route('/create_bill', methods=['GET', 'POST'])
@login_required
def create_bill():
    if request.method == 'POST':
        # Basic Bill Details
        bill_number = request.form['bill_number']
        purchase_order_id = request.form['purchase_order_id']
        bill_date = datetime.strptime(request.form['bill_date'], '%Y-%m-%d')
        status = request.form['status']

        # Calculate Total Amount based on line items
        total_amount = 0

        # Create a New Bill Object
        new_bill = Bill(
            bill_number=bill_number,
            purchase_order_id=purchase_order_id,
            bill_date=bill_date,
            total_amount=0,  # Will update later after adding line items
            status=status
        )
        db.session.add(new_bill)
        db.session.commit()

        # Handle Line Items
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            # Calculate the total price for the line item
            quantity = int(quantity)
            unit_price = float(unit_price)
            total_price = quantity * unit_price

            # Create and add a new line item for the bill
            new_line_item = BillLineItem(
                bill_id=new_bill.id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            db.session.add(new_line_item)

            # Update the total amount of the bill
            total_amount += total_price

        # Update the total amount of the bill and commit changes
        new_bill.total_amount = total_amount
        db.session.commit()

        flash('Bill created successfully!', 'success')
        return redirect(url_for('bill_list'))

    # Load purchase orders to show in dropdown
    purchase_orders = PurchaseOrder.query.all()
    return render_template('bill_form.html', purchase_orders=purchase_orders, show_logo=True, active_tab='bill_list')


# Edit Bill
# Edit Bill
@app.route('/edit_bill/<int:bill_id>', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)

    if request.method == 'POST':
        # Update Bill Details
        bill.bill_number = request.form['bill_number']
        bill.purchase_order_id = request.form['purchase_order_id']
        bill.bill_date = datetime.strptime(request.form['bill_date'], '%Y-%m-%d')
        bill.status = request.form['status']

        # Calculate new total amount based on line items
        total_amount = 0

        # Delete existing line items
        BillLineItem.query.filter_by(bill_id=bill.id).delete()

        # Handle Line Items
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            # Calculate total price for the line item
            quantity = int(quantity)
            unit_price = float(unit_price)
            total_price = quantity * unit_price

            # Create a new line item
            new_line_item = BillLineItem(
                bill_id=bill.id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            db.session.add(new_line_item)

            # Update the total amount of the bill
            total_amount += total_price

        # Update the total amount of the bill and commit changes
        bill.total_amount = total_amount
        db.session.commit()

        flash('Bill updated successfully!', 'success')
        return redirect(url_for('bill_list'))

    # Load purchase orders to show in dropdown and existing line items for the bill
    purchase_orders = PurchaseOrder.query.all()
    return render_template('bill_form.html', bill=bill, purchase_orders=purchase_orders, show_logo=True, active_tab='bill_list')


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
@app.route('/purchase_order', methods=['GET', 'POST'])
@login_required
def purchase_order():
    if request.method == 'POST':
        vendor_id = request.form['vendor_id']
        order_date = request.form['order_date']
        total_amount = request.form['total_amount']
        status = request.form['status']

        new_order = PurchaseOrder(
            vendor_id=vendor_id,
            order_date=datetime.strptime(order_date, '%Y-%m-%d'),
            total_amount=total_amount,
            status=status
        )
        db.session.add(new_order)
        db.session.commit()

        # Add line items
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for item_name, quantity, unit_price in zip(item_names, quantities, unit_prices):
            new_line_item = LineItem(
                purchase_order_id=new_order.id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price
            )
            db.session.add(new_line_item)

        db.session.commit()
        flash('Purchase Order created successfully!', 'success')
        return redirect(url_for('purchase_order_list'))

    vendors = Vendor.query.all()  # Get the list of vendors for the dropdown
    return render_template('purchase_order.html', vendors=vendors, show_logo=True, active_tab='purchase_order')


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

        # Commit the changes to the database
        db.session.commit()
        flash('Purchase Order updated successfully!', 'success')
        return redirect(url_for('purchase_order_list'))

    # If the request method is GET, show the form to edit the order
    vendors = Vendor.query.all()
    line_items = LineItem.query.filter_by(purchase_order_id=order_id).all()

    return render_template('edit_purchase_order.html', order=order, vendors=vendors, line_items=line_items,
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


if __name__ == '__main__':
    app.run(debug=True)
