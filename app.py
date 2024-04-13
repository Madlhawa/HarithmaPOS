from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:''@localhost/harithma'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

db = SQLAlchemy(app)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.Integer)
    vehicals = db.relationship('Vehical', backref='owner', lazy=True)

    def __repr__(self):
        return f"Customer('{self.name}','{self.contact}')"

class Vehical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(8), nullable=False)
    make = db.Column(db.String(20))
    model = db.Column(db.String(20))
    year = db.Column(db.String(4))
    owner_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

    def __repr__(self):
        return f"Vehical('{self.number}','{self.make}','{self.model}','{self.year}')"

@app.route('/customer/')
def customer():
    customers = Customer.query.all()
    return render_template('index.html', customers = customers)

@app.route('/insert_customer/', methods = ['POST'])
def insert_customer():
    if request.method == "POST":
        customer = Customer(
            name = request.form.get('name'),
            contact = request.form.get('contact')
        )
        db.session.add(customer)
        db.session.commit()
        flash("Customer added successfully!")
        return redirect(url_for('index'))
    
@app.route('/update_customer/', methods = ['POST'])
def update_customer():
    if request.method == "POST":
        customer = Customer.query.get(request.form.get('id'))
        customer.name = request.form['name']
        customer.contact = request.form['contact']
        db.session.commit()
        flash("Customer is updated!")
        return redirect(url_for('index'))
    
@app.route('/delete_customer/<id>', methods = ['GET', 'POST'])
def delete_customer(id):
    customer = Customer.query.get(id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer is deleted!")
    return redirect(url_for('index'))

@app.route('/insert_vehical/', methods = ['POST'])
def insert_vehical():
    if request.method == "POST":
        vehical = Vehical(
            number = request.form.get('number'),
            make = request.form.get('make'),
            model = request.form.get('model'),
            year = request.form.get('year'),
            owner_id = request.form.get('owner_id'),
        )
        db.session.add(vehical)
        db.session.commit()
        flash("Vehical added successfully!")
        return redirect(url_for('index'))

@app.route('/update_vehical/', methods = ['POST'])
def update_vehical():
    if request.method == "POST":
        vehical = Vehical.query.get(request.form.get('id'))
        vehical.number = request.form['number']
        vehical.make = request.form['make']
        vehical.model = request.form['model']
        vehical.year = request.form['year']
        vehical.owner_id = request.form['owner_id']
        db.session.commit()
        flash("Vehical is updated!")
        return redirect(url_for('index'))
    
@app.route('/delete_vehical/<id>', methods = ['GET', 'POST'])
def delete_vehical(id):
    vehical = Vehical.query.get(id)
    db.session.delete(vehical)
    db.session.commit()
    flash("Vehical is deleted!")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)