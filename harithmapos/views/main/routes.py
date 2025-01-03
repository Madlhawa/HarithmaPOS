from flask import Blueprint, render_template, request, jsonify

main_blueprint = Blueprint('main_blueprint', __name__)

# Sample data for search
data = ["Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig", "Grape"]

@main_blueprint.route("/", methods=['GET', 'POST'])
def home():
    return render_template('index.html', title='Home')

@main_blueprint.route("/test", methods=['GET', 'POST'])
def test():
    return render_template('test.html', title='Home')

@main_blueprint.route('/app/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()  # Get the query parameter
    results = [item for item in data if query in item.lower()]  # Filter data
    return jsonify(results)  # Return filtered results as JSON