from flask import Blueprint, render_template

main_blueprint = Blueprint('main_blueprint', __name__)

@main_blueprint.route('/test/')
def test():
    return render_template('test.html')

@main_blueprint.route('/test1/')
def test1():
    return render_template('test1.html')