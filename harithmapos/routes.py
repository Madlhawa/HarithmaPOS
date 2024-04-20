from flask import render_template, request, redirect, url_for, flash
from harithmapos import app, db
from harithmapos.forms import RegistrationForm, LoginForm, CustomerForm, VehicalForm
from harithmapos.models import Customer, Vehical

@app.route('/', methods = ['GET', 'POST'])
@app.route('/customer/', methods = ['GET', 'POST'])
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
def delete_customer(id):
    customer = db.session.get(Customer, id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer is deleted!", category="success")
    return redirect(url_for('customer'))

@app.route('/insert_vehical/', methods = ['GET', 'POST'])
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
def delete_vehical(id):
    vehical = Vehical.query.get(id)
    db.session.delete(vehical)
    db.session.commit()
    flash("Vehical is deleted!", category='success')
    return redirect(url_for('customer'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash(f'Account created for {form.name.data}.',category='success')
        return redirect(url_for('customer'))
    return render_template('register.html', title='Register', form = form)

@app.route("/login", methods=['GET', 'POST'])
@app.route("/login")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.email.data == 'admin@email.com' and form.password.data == 'password':
            flash(f'You have been logged in successfully.',category='success')
            return redirect(url_for('customer'))
        else:
            flash(f'Login unsuccessfull. Please check username and password.',category='danger')
    return render_template('login.html', title='Login', form = form)

@app.route('/test/')
def test():
    return render_template('test.html')