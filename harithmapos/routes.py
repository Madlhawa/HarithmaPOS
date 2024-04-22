import os
import secrets
from PIL import Image
from harithmapos import app, db, bcrypt
from harithmapos.models import Customer, Vehical, User, Supplier
from flask import render_template, request, redirect, url_for, flash
from harithmapos.forms import SearchForm, UserRegisterForm, UserLoginForm, UserUpdateForm, CustomerForm, VehicalForm, SupplierCreateForm, SupplierUpdateForm
from flask_login import login_user, logout_user, login_required, current_user

@app.route('/supplier/<int:supplier_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    flash("Supplier is deleted!", category='success')
    return redirect(url_for('supplier'))

@app.route("/supplier/<int:supplier_id>/update", methods=['GET', 'POST'])
@login_required
def update_supplier(supplier_id):
    supplier_update_form = SupplierUpdateForm()
    if supplier_update_form.validate_on_submit():
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.name = supplier_update_form.name.data
        supplier.contact = supplier_update_form.contact.data
        supplier.address = supplier_update_form.address.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('supplier'))

@app.route("/supplier/create", methods=['GET', 'POST'])
@login_required
def insert_supplier():
    supplier_create_form = SupplierCreateForm()
    if supplier_create_form.validate_on_submit():
        supplier = Supplier(
            name = supplier_create_form.name.data,
            contact = supplier_create_form.contact.data,
            address = supplier_create_form.address.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash("Supplier added successfully!", category='success')
    else:
        flash("Supplier failed to add!", category='danger')
    return redirect(url_for('supplier'))

@app.route("/supplier", methods=['GET', 'POST'])
@login_required
def supplier():
    page = request.args.get('page',1,type=int)
    supplier_create_form = SupplierCreateForm()
    supplier_update_form = SupplierUpdateForm()
    search_form = SearchForm()
    print(f'{search_form.query.data = }')
    if search_form.validate_on_submit():
        print(f'{search_form.query.data = }')
        suppliers = Supplier.query.order_by(Supplier.update_dttm.desc()).filter(Supplier.name.icontains(search_form.query.data)).paginate(page=page, per_page=5)
    else:
        suppliers = Supplier.query.order_by(Supplier.update_dttm.desc()).paginate(page=page, per_page=5)
    return render_template(
        'supplier.html', 
        title='Supplier', 
        supplier_create_form=supplier_create_form, 
        supplier_update_form=supplier_update_form, 
        search_form=search_form,
        suppliers=suppliers
    )

def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, file_extention = os.path.splitext(form_image.filename)
    image_file_name = random_hex + file_extention
    image_path = os.path.join(app.root_path, 'static/user_images', image_file_name)

    output_size = (125,125)
    i = Image.open(form_image)
    i.thumbnail(output_size)
    i.save(image_path)

    return image_file_name

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form=UserUpdateForm()
    if form.validate_on_submit():
        if form.image.data:
            if current_user.image != 'default.jpg':
                os.remove(os.path.join(app.root_path, 'static/user_images', current_user.image))
            image = save_image(form.image.data)
            current_user.image = image
            print(f'{image = }')
        current_user.email = form.email.data
        current_user.name = form.name.data
        db.session.commit()
        flash('Account has been updated.',category='success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
    image_path = url_for('static', filename=f'user_images/{current_user.image}')
    print(f'{image_path = }')
    return render_template('account.html', title='Account', user_image_file=image_path, form=form)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer'))
    form = UserRegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            name=form.name.data, 
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Account has been created. Please login.',category='success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form = form)

@app.route("/", methods=['GET', 'POST'])
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('customer'))
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('customer'))
        else:
            flash(f'Login unsuccessfull. Please check email and password.', category='danger')
    return render_template('login.html', title='Login', form = form)

@app.route('/customer/', methods = ['GET', 'POST'])
@login_required
def customer():
    customer_form = CustomerForm()
    vehical_form = VehicalForm()
    if request.method == 'POST' and 'query' in request.form:
        query = request.form["query"]
        customers = Customer.query.filter(Customer.name.icontains(query)).all()
        return render_template('customer.html', title='Customers', customer_form=customer_form, vehical_form=vehical_form, customers=customers, query=query)
    else:
        customers = Customer.query.all()
        return render_template('customer.html', title='Customers', customer_form=customer_form, vehical_form=vehical_form, customers=customers)

@app.route('/insert_customer/', methods = ['POST'])
@login_required
def insert_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name = form.name.data,
            contact = form.contact.data,
            address = form.address.data,
            email = form.email.data,
        )
        db.session.add(customer)
        db.session.commit()
        flash("Customer added successfully.", category='success')
    else:
        flash("Customer failed to add.", category='danger')
    return redirect(url_for('customer'))

@app.route('/update_customer/', methods = ['POST'])
@login_required
def update_customer():
    form = CustomerForm()
    print(f"{request.form.get('id') = }")
    if form.validate_on_submit():
        customer = db.session.get(Customer, request.form.get('id'))
        customer.name = form.name.data
        customer.contact = form.contact.data
        customer.address = form.address.data
        customer.email = form.email.data
        db.session.commit()
        flash("Customer updated successfully.", category='success')
    else:
        flash("Customer failed to update", category='danger')
    return redirect(url_for('customer'))
 
@app.route('/delete_customer/<id>', methods = ['GET', 'POST'])
@login_required
def delete_customer(id):
    customer = db.session.get(Customer, id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer is deleted!", category="success")
    return redirect(url_for('customer'))

@app.route('/insert_vehical/', methods = ['GET', 'POST'])
@login_required
def insert_vehical():
    form = VehicalForm()
    if form.validate_on_submit():
        vehical = Vehical(
            number = form.number.data,
            make = form.make.data,
            model = form.model.data,
            year = form.year.data,
            owner_id = form.owner_id.data
        )
        db.session.add(vehical)
        db.session.commit()
        flash("Vehical added successfully!", category='success')
    else:
        flash("Vehical failed to add!", category='danger')
    return redirect(url_for('customer'))

@app.route('/update_vehical/', methods = ['POST'])
@login_required
def update_vehical():
    form = VehicalForm()
    if form.validate_on_submit():
        vehical = db.session.get(Vehical, request.form.get('id'))
        vehical.number = form.number.data
        vehical.make = form.make.data
        vehical.model = form.model.data
        vehical.year = form.year.data
        vehical.owner_id = form.owner_id.data
        db.session.commit()
        flash("Vehical is updated!", category='success')
    else:
        flash("Vehical failed to add!", category='danger')
    return redirect(url_for('customer'))

@app.route('/delete_vehical/<id>', methods = ['GET', 'POST'])
@login_required
def delete_vehical(id):
    vehical = Vehical.query.get(id)
    db.session.delete(vehical)
    db.session.commit()
    flash("Vehical is deleted!", category='success')
    return redirect(url_for('customer'))

@app.route('/test/')
def test():
    return render_template('test.html')