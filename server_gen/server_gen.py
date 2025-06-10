# Creo il file server_gen.py
from flask import Flask, request, jsonify, g
import database_gen
from database_gen import Session
import os
import logging

if os.environ.get('FLASK_ENV') != 'development':
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)


app = Flask(__name__)

# Initialize database
database_gen.init_db()

# Middleware to create and close database session for each request
@app.before_request
def create_session():
    g.session = Session()

# Ensure the session is available in the global context
@app.teardown_appcontext
def close_session(exception=None):
    session = g.pop('session', None)
    if session is not None:
        if exception:
            session.rollback()
        session.close()

####
# API for Group
####

# return a list of all groups (group_id and name)
@app.route('/api/groups', methods=['GET'])
def get_groups():
    groups = database_gen.get_all_groups(g.session)
    return jsonify([{
        "group_id": group.group_id,
        "name": group.name,
    } for group in groups])

# return a specific group by id (name)
@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    group = database_gen.get_group(g.session, group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    return jsonify({
        "group_id": group.group_id,
        "name": group.name
    })

# create a new group with name
@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        group = database_gen.create_group(
            g.session,
            data['name']
        )
        return jsonify({
            "group_id": group.group_id,
            "name": group.name
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing group by id with optional name
@app.route('/api/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_gen.update_group(
            g.session,
            group_id,
            data.get('name')
        )
        if not success:
            return jsonify({"error": "Group not found"}), 404

        group = database_gen.get_group(g.session, group_id)
        return jsonify({
            "group_id": group.group_id,
            "name": group.name
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a group by id only if it has no dependencies
@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    try:
        success, message = database_gen.delete_group(g.session, group_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete group" in message else 404

        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Group by id (group and all its dependencies)
@app.route('/api/groups/<int:group_id>/deep-delete', methods=['DELETE'])
def deep_delete_group_api(group_id):
    try:
        success, message = database_gen.deep_delete_group(g.session, group_id)
        
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        
        return jsonify({
            "message": message,
            "group_id": group_id,
            "operation": "deep_delete"
        }), 200
        
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

####
# API for Component
####

# return a list of all components (component_id, name, type, x, y, group_id)
@app.route('/api/components', methods=['GET'])
def get_components():
    components = database_gen.get_all_components(g.session)
    return jsonify([{
        "component_id": component.component_id,
        "name": component.name,
        "type": component.type,
        "x": component.x,
        "y": component.y,
        "group_id": component.group_id
    } for component in components])

# return a specific component by id (name, type, general_info, x, y, group_id)
@app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    component = database_gen.get_component(g.session, component_id)
    if not component:
        return jsonify({"error": "Component not found"}), 404

    return jsonify({
        "component_id": component.component_id,
        "name": component.name,
        "type": component.type,
        "general_info": component.general_info,
        "x": component.x,
        "y": component.y,
        "group_id": component.group_id
    })

# return a list of all components for a specific group (component_id, name, type, x, y)
@app.route('/api/groups/<int:group_id>/components', methods=['GET'])
def get_components_by_group(group_id):
    components = database_gen.get_components_by_group(g.session, group_id)
    return jsonify([{
        "component_id": component.component_id,
        "name": component.name,
        "type": component.type,
        "x": component.x,
        "y": component.y
    } for component in components])

# create a new component with name and optional type, general_info, x, y, group_id
@app.route('/api/components', methods=['POST'])
def create_component():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        component = database_gen.create_component(
            g.session,
            data['name'],
            data.get('type'),
            data.get('general_info'),
            data.get('x'),
            data.get('y'),
            data.get('group_id')
        )
        return jsonify({
            "component_id": component.component_id,
            "name": component.name,
            "type": component.type,
            "general_info": component.general_info,
            "x": component.x,
            "y": component.y,
            "group_id": component.group_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing component by id with optional name, type, general_info, x, y, group_id
@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_gen.update_component(
            g.session,
            component_id,
            data.get('name'),
            data.get('type'),
            data.get('general_info'),
            data.get('x'),
            data.get('y'),
            data.get('group_id')
        )
        if not success:
            return jsonify({"error": "Component not found"}), 404

        component = database_gen.get_component(g.session, component_id)
        return jsonify({
            "component_id": component.component_id,
            "name": component.name,
            "type": component.type,
            "general_info": component.general_info,
            "x": component.x,
            "y": component.y,
            "group_id": component.group_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a component by id
@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component_api(component_id):
    try:
        success, message = database_gen.delete_component(g.session, component_id)
        if not success:
            return jsonify({"error": message}), 404
        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

####
# API for general operations
####

# Clear the entire database
@app.route('/api/clear-database', methods=['DELETE'])
def clear_database():
    try:
        success = database_gen.clear_all_database(g.session)
        if success:
            return jsonify({"message": "Database cleared successfully"})
        else:
            return jsonify({"error": "Failed to clear database"}), 500
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Gen Server",
        "port": 5003
    })

# Run the Flask application for server Gen
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)