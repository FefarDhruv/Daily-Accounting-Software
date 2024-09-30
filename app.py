from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect  # Import CSRF protection
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration (SQLite for simplicity, can be changed to MySQL or PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CSRF Protection
csrf = CSRFProtect(app)

db = SQLAlchemy(app)

# Models
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(100), nullable=False)
    gst_number = db.Column(db.String(15), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    org_type = db.Column(db.String(50), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)  # Store hashed passwords
    role = db.Column(db.String(50), nullable=False)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    email_id = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(255), nullable=False)

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


# Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['userId']
        password = request.form['password']

        # Dummy login check for now
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
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


# Setup Organization Page
@app.route('/setup_organization', methods=['GET', 'POST'])
@login_required
def setup_organization():
    if request.method == 'POST':
        org_name = request.form['org_name']
        gst_number = request.form['gst_number']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']
        contact_person = request.form['contact_person']
        org_type = request.form['org_type']

        new_org = Organization(
            org_name=org_name,
            gst_number=gst_number,
            email_id=email_id,
            phone_number=phone_number,
            address=address,
            contact_person=contact_person,
            org_type=org_type
        )
        db.session.add(new_org)
        db.session.commit()

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

        for username, password, role in zip(usernames, passwords, roles):
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)

        db.session.commit()
        flash('Users added successfully!', 'success')
        return redirect(url_for('vendor_list'))

    return render_template('add_users.html', show_logo=True, show_navbar=False)



# Vendor List Page
# Vendor List Page
@app.route('/vendor_list')
@login_required
def vendor_list():
    vendors = Vendor.query.all()  # Fetch all vendors from the database
    return render_template('vendor_list.html', vendors=vendors, show_logo=True, active_tab='vendor_list')


# Add New Vendor (Vendor Master Form)
@app.route('/vendor_master', methods=['GET', 'POST'])
@login_required
def vendor_master():
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        company_name = request.form['company_name']
        email_id = request.form['email_id']
        phone_number = request.form['phone_number']
        address = request.form['address']

        new_vendor = Vendor(
            vendor_name=vendor_name,
            company_name=company_name,
            email_id=email_id,
            phone_number=phone_number,
            address=address
        )
        db.session.add(new_vendor)
        db.session.commit()

        flash('Vendor added successfully!', 'success')
        return redirect(url_for('vendor_list'))

    return render_template('vendor_master.html', show_logo=True, active_tab='vendor_master')


# Purchase Order List Page
@app.route('/purchase_order_list')
@login_required
def purchase_order_list():
    purchase_orders = PurchaseOrder.query.all()  # Fetch all purchase orders
    return render_template('purchase_order_list.html', purchase_orders=purchase_orders, show_logo=True, active_tab='purchase_order')


# Update Order Status via AJAX (for Kanban)
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')  # Extract the new status from the request body

    order = PurchaseOrder.query.get_or_404(order_id)  # Find the purchase order by ID

    if new_status in ['Pending', 'Completed', 'Cancelled']:
        order.status = new_status.capitalize()  # Capitalize the new status for consistency
        db.session.commit()  # Commit the changes to the database
        return jsonify({'message': 'Order status updated successfully!'}), 200
    else:
        return jsonify({'message': 'Invalid status'}), 400


# Update Order Status via Form (for Table View)
@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if new_status:
        order.status = new_status
        db.session.commit()
        flash('Purchase Order status updated successfully!', 'success')
    else:
        flash('Failed to update the status. Please try again.', 'danger')

    return redirect(url_for('purchase_order_list'))


# Purchase Order Form Page
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
    order = PurchaseOrder.query.get_or_404(order_id)

    if request.method == 'POST':
        # Update the purchase order
        order.vendor_id = request.form['vendor_id']
        order.order_date = request.form['order_date']
        order.total_amount = request.form['total_amount']
        order.status = request.form['status']
        db.session.commit()

        # Update line items
        item_ids = request.form.getlist('item_id[]')
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for i, item_id in enumerate(item_ids):
            line_item = LineItem.query.get(item_id)
            line_item.item_name = item_names[i]
            line_item.quantity = quantities[i]
            line_item.unit_price = unit_prices[i]

        db.session.commit()
        flash('Purchase Order updated successfully!', 'success')
        return redirect(url_for('purchase_order_list'))

    vendors = Vendor.query.all()
    line_items = LineItem.query.filter_by(purchase_order_id=order_id).all()

    return render_template('edit_purchase_order.html', order=order, vendors=vendors, line_items=line_items,
                           show_logo=True, active_tab='purchase_order')


# Delete Purchase Order
@app.route('/delete_purchase_order/<int:order_id>', methods=['POST'])
@login_required
def delete_purchase_order(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()

    flash('Purchase Order deleted successfully!', 'success')
    return redirect(url_for('purchase_order_list'))


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

    # Check if the vendor has related purchase orders
    # if vendor.purchase_orders:
    #     flash('Cannot delete vendor. There are existing purchase orders associated with this vendor.', 'danger')
    #     return redirect(url_for('vendor_list'))

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
