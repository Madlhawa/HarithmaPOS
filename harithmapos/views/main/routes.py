from flask import Blueprint, render_template, request, jsonify

main_blueprint = Blueprint('main_blueprint', __name__)

# Sample data for search
data = ["Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig", "Grape"]

@main_blueprint.route('/test/')
def test():
    return render_template('test.html')

@main_blueprint.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()  # Get the query parameter
    results = [item for item in data if query in item.lower()]  # Filter data
    return jsonify(results)  # Return filtered results as JSON

@main_blueprint.route('/test1/')
def test1():
    return render_template('test1.html')