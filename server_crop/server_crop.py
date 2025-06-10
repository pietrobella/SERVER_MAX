from flask import Flask, request, jsonify, render_template_string, send_file, g
import io
import database_crop
from database_crop import Session
import os
import logging

if os.environ.get('FLASK_ENV') != 'development':
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

app = Flask(__name__)

# Inizializza il database
database_crop.init_db()

# Gestione della sessione
@app.before_request
def create_session():
    g.session = Session()

@app.teardown_appcontext
def close_session(exception=None):
    session = g.pop('session', None)
    if session is not None:
        if exception:
            session.rollback()
        session.close()

# API per Board
@app.route('/api/boards', methods=['GET'])
def get_boards():
    try:
        boards = database_crop.get_all_boards()
        return jsonify(boards)
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/boards/<int:board_id>', methods=['GET'])
def get_board(board_id):
    try:
        board = database_crop.get_board(board_id)
        if board:
            return jsonify(board)
        return jsonify({"error": "Board not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/boards', methods=['POST'])
def add_board():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing board name"}), 400

    try:
        board_id = database_crop.add_board(data['name'])
        return jsonify({
            "message": "Board added successfully",
            "id": board_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/boards/<int:board_id>', methods=['PUT'])
def update_board(board_id):
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing board name"}), 400

    try:
        if database_crop.update_board(board_id, data['name']):
            return jsonify({"message": "Board updated successfully"})
        return jsonify({"error": "Board not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/boards/<int:board_id>', methods=['DELETE'])
def delete_board(board_id):
    try:
        if database_crop.delete_board(board_id):
            return jsonify({"message": "Board deleted successfully"})
        return jsonify({"error": "Board not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Component
@app.route('/api/components', methods=['GET'])
def get_components():
    try:
        return jsonify(database_crop.get_all_components())
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    try:
        component = database_crop.get_component(component_id)
        if component:
            return jsonify(component)
        return jsonify({"error": "Component not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/components', methods=['POST'])
def add_component():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing component name"}), 400

    try:
        board_id = data.get('board_id')
        more_info = data.get('more_info')

        if more_info and len(more_info) > 1000:
            return jsonify({"error": "More info exceeds 1000 characters limit"}), 400

        component_id = database_crop.add_component(data['name'], more_info, board_id)
        return jsonify({
            "message": "Component added successfully",
            "id": component_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing component name"}), 400

    try:
        board_id = data.get('board_id')
        more_info = data.get('more_info')

        if more_info and len(more_info) > 1000:
            return jsonify({"error": "More info exceeds 1000 characters limit"}), 400

        if database_crop.update_component(component_id, data['name'], more_info, board_id):
            return jsonify({"message": "Component updated successfully"})
        return jsonify({"error": "Component not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component(component_id):
    try:
        if database_crop.delete_component(component_id):
            return jsonify({"message": "Component deleted successfully"})
        return jsonify({"error": "Component not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Schematic
@app.route('/api/schematics', methods=['GET'])
def get_schematics():
    try:
        return jsonify(database_crop.get_all_schematics())
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/schematics/<int:schematic_id>', methods=['GET'])
def get_schematic(schematic_id):
    try:
        schematic = database_crop.get_schematic(schematic_id)
        if schematic:
            return jsonify(schematic)
        return jsonify({"error": "Schematic not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/schematics/<int:schematic_id>/image', methods=['GET'])
def get_schematic_image(schematic_id):
    try:
        image_data = database_crop.get_schematic_image(schematic_id)
        if image_data:
            return send_file(
                io.BytesIO(image_data),
                mimetype='image/jpeg',
                as_attachment=False
            )
        return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/schematics', methods=['POST'])
def add_schematic():
    try:
        image_file = request.files['image']
        image_data = image_file.read()
        name = request.form.get('name')
        board_id = request.form.get('board_id')
        
        # Converti board_id in intero se non è None
        if board_id:
            board_id = int(board_id)

        schematic_id = database_crop.add_schematic(name, image_data, board_id)
        return jsonify({
            "message": "Schematic added successfully",
            "id": schematic_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/schematics/<int:schematic_id>', methods=['PUT'])
def update_schematic(schematic_id):
    try:
        image_file = request.files['image']
        image_data = image_file.read()
        name = request.form.get('name')
        board_id = request.form.get('board_id')
        
        # Converti board_id in intero se non è None
        if board_id:
            board_id = int(board_id)

        if database_crop.update_schematic(schematic_id, name, image_data, board_id):
            return jsonify({"message": "Schematic updated successfully"})
        return jsonify({"error": "Schematic not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/schematics/<int:schematic_id>', methods=['DELETE'])
def delete_schematic(schematic_id):
    try:
        if database_crop.delete_schematic(schematic_id):
            return jsonify({"message": "Schematic deleted successfully"})
        return jsonify({"error": "Schematic not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Placement
@app.route('/api/placements', methods=['GET'])
def get_placements():
    try:
        return jsonify(database_crop.get_all_placements())
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/placements/<int:placement_id>', methods=['GET'])
def get_placement(placement_id):
    try:
        placement = database_crop.get_placement(placement_id)
        if placement:
            return jsonify(placement)
        return jsonify({"error": "Placement not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/placements/<int:placement_id>/image', methods=['GET'])
def get_placement_image(placement_id):
    try:
        image_data = database_crop.get_placement_image(placement_id)
        if image_data:
            return send_file(
                io.BytesIO(image_data),
                mimetype='image/jpeg',
                as_attachment=False
            )
        return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/placements', methods=['POST'])
def add_placement():
    try:
        image_file = request.files['image']
        image_data = image_file.read()
        name = request.form.get('name')
        side = request.form.get('side')
        board_id = request.form.get('board_id')
        
        # Converti board_id in intero se non è None
        if board_id:
            board_id = int(board_id)

        placement_id = database_crop.add_placement(name, side, image_data, board_id)
        return jsonify({
            "message": "Placement added successfully",
            "id": placement_id
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/placements/<int:placement_id>', methods=['PUT'])
def update_placement(placement_id):
    try:
        image_file = request.files['image']
        image_data = image_file.read()
        name = request.form.get('name')
        side = request.form.get('side')
        board_id = request.form.get('board_id')
        
        # Converti board_id in intero se non è None
        if board_id:
            board_id = int(board_id)

        if database_crop.update_placement(placement_id, name, side, image_data, board_id):
            return jsonify({"message": "Placement updated successfully"})
        return jsonify({"error": "Placement not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/placements/<int:placement_id>', methods=['DELETE'])
def delete_placement(placement_id):
    try:
        if database_crop.delete_placement(placement_id):
            return jsonify({"message": "Placement deleted successfully"})
        return jsonify({"error": "Placement not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Component-Placement
@app.route('/api/component-placements/<int:component_id>', methods=['GET'])
def get_component_placement(component_id):
    try:
        cp = database_crop.get_component_placements(component_id)
        if cp:
            return jsonify(cp)
        return jsonify({"error": "Component-placement association not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-placements', methods=['POST'])
def add_component_placement():
    data = request.json
    if not data or not all(k in data for k in ['component_id', 'placement_id', 'x', 'y']):
        return jsonify({"error": "Missing data"}), 400

    try:
        database_crop.add_component_placement(
            data['component_id'],
            data['placement_id'],
            data['x'],
            data['y']
        )
        return jsonify({"message": "Component-placement association added successfully"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-placements/<int:component_id>', methods=['PUT'])
def update_component_placement(component_id):
    data = request.json
    if not data or not all(k in data for k in ['placement_id', 'x', 'y']):
        return jsonify({"error": "Missing data"}), 400

    try:
        if database_crop.update_component_placement(
            component_id,
            data['placement_id'],
            data['x'],
            data['y']
        ):
            return jsonify({"message": "Component-placement association updated successfully"})
        return jsonify({"error": "Component-placement association not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-placements/<int:component_id>', methods=['DELETE'])
def delete_component_placement(component_id):
    try:
        if database_crop.delete_component_placement(component_id):
            return jsonify({"message": "Component-placement association deleted successfully"})
        return jsonify({"error": "Component-placement association not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Component-Schematic
@app.route('/api/component-schematics/<int:component_id>', methods=['GET'])
def get_component_schematics(component_id):
    try:
        cs_list = database_crop.get_component_schematics(component_id)
        return jsonify(cs_list)
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-schematics', methods=['POST'])
def add_component_schematic():
    data = request.json
    if not data or not all(k in data for k in ['component_id', 'schematic_id', 'x', 'y']):
        return jsonify({"error": "Missing data"}), 400

    try:
        database_crop.add_component_schematic(
            data['component_id'],
            data['schematic_id'],
            data['x'],
            data['y']
        )
        return jsonify({"message": "Component-schematic association added successfully"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-schematics/<int:component_id>/<int:schematic_id>', methods=['PUT'])
def update_component_schematic(component_id, schematic_id):
    data = request.json
    if not data or not all(k in data for k in ['x', 'y']):
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        if database_crop.update_component_schematic(
            component_id,
            schematic_id,
            data['x'],
            data['y']
        ):
            return jsonify({"message": "Component-schematic association updated successfully"})
        return jsonify({"error": "Component-schematic association not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/component-schematics/<int:component_id>/<int:schematic_id>', methods=['DELETE'])
def delete_component_schematic(component_id, schematic_id):
    try:
        if database_crop.delete_component_schematic(component_id, schematic_id):
            return jsonify({"message": "Component-schematic association deleted successfully"})
        return jsonify({"error": "Component-schematic association not found"}), 404
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear-database', methods=['DELETE'])
def clear_database():
    try:
        if database_crop.clear_all_database():
            return jsonify({"message": "Database cleared successfully"})
        return jsonify({"message": "Database was already empty"}), 200
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Avvio del server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)