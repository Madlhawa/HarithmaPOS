from __main__ import app
from app import Customer
from flask import Flask, render_template, request, redirect, url_for, flash

@app.route('/employee/')
def employee():
    customers = Customer.query.all()
    return render_template('index.html', customers = customers)