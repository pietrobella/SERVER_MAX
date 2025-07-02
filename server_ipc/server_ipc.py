import base64
from flask import Flask, request, jsonify, g
import database_ipc
from database_ipc import Session
import os
import logging
from voice_assistant_for_server import process_query, process_wav_file

if os.environ.get('FLASK_ENV') != 'development':
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

from werkzeug.utils import secure_filename
from read_IPC import parse_ipc2581_and_populate_db
import sys

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'cvg', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
database_ipc.init_db()

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

################################################################
# API for Board
################################################################

# return a list of all boards (id and name)
@app.route('/api/boards', methods=['GET'])
def get_boards():
    boards = database_ipc.get_all_boards(g.session)
    return jsonify([{
        "id": board.id,
        "name": board.name,
    } for board in boards])

# return a specific board by id (name and polygon)
@app.route('/api/boards/<int:board_id>', methods=['GET'])
def get_board(board_id):
    board = database_ipc.get_board(g.session, board_id)
    if not board:
        return jsonify({"error": "Board not found"}), 404

    return jsonify({
        "name": board.name,
        "polygon": board.polygon
    })

# create a new board with name and optional polygon
@app.route('/api/boards', methods=['POST'])
def create_board():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        board = database_ipc.create_board(
            g.session,
            data['name'],
            data.get('polygon')
        )
        return jsonify({
            "id": board.id,
            "name": board.name,
            "polygon": board.polygon
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing board by id with optional name and polygon
@app.route('/api/boards/<int:board_id>', methods=['PUT'])
def update_board(board_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_board(
            g.session,
            board_id,
            data.get('name'),
            data.get('polygon')
        )
        if not success:
            return jsonify({"error": "Board not found"}), 404

        board = database_ipc.get_board(g.session, board_id)
        return jsonify({
            "id": board.id,
            "name": board.name,
            "polygon": board.polygon
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a board by id only if it has no dependencies
@app.route('/api/boards/<int:board_id>', methods=['DELETE'])
def delete_board(board_id):
    try:
        success, message = database_ipc.delete_board(g.session, board_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete board" in message else 404

        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Board by id (board and all its dependencies)
@app.route('/api/boards/<int:board_id>/deep-delete', methods=['DELETE'])
def deep_delete_board_api(board_id):

    try:
        success, message = database_ipc.deep_delete_board(g.session, board_id)
        
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        
        return jsonify({
            "message": message,
            "board_id": board_id,
            "operation": "deep_delete"
        }), 200
        
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


################################################################
# API for Package
################################################################

# return a list of all packages (id, name, height, polygon)
@app.route('/api/packages', methods=['GET'])
def get_packages():
    packages = database_ipc.get_all_packages(g.session)
    return jsonify([{
        "id": package.id,
        "name": package.name,
    } for package in packages])

# return a specific package by id (name, height, polygon)
@app.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package(package_id):
    package = database_ipc.get_package(g.session, package_id)
    if not package:
        return jsonify({"error": "Package not found"}), 404

    return jsonify({
        "name": package.name,
        "height": package.height,
        "polygon": package.polygon
    })

# create a new package with name, optional height and polygon
@app.route('/api/packages', methods=['POST'])
def create_package():
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        package = database_ipc.create_package(
            g.session,
            data['name'],
            data.get('height'),
            data.get('polygon')
        )
        return jsonify({
            "id": package.id,
            "name": package.name,
            "height": package.height,
            "polygon": package.polygon
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing package by id with optional name, height and polygon
@app.route('/api/packages/<int:package_id>', methods=['PUT'])
def update_package(package_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_package(
            g.session,
            package_id,
            data.get('name'),
            data.get('height'),
            data.get('polygon')
        )
        if not success:
            return jsonify({"error": "Package not found"}), 404

        package = database_ipc.get_package(g.session, package_id)
        return jsonify({
            "id": package.id,
            "name": package.name,
            "height": package.height,
            "polygon": package.polygon
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a package by id only if it has no dependencies
@app.route('/api/packages/<int:package_id>', methods=['DELETE'])
def delete_package(package_id):
    try:
        success, message = database_ipc.delete_package(g.session, package_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete package" in message else 404
        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Package by id (package and all its dependencies)
@app.route('/api/packages/<int:package_id>/deep-delete', methods=['DELETE'])
def deep_delete_package_api(package_id):
    try:
        success, message = database_ipc.deep_delete_package(g.session, package_id)
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        return jsonify({
            "message": message,
            "package_id": package_id,
            "operation": "deep_delete"
        }), 200
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    

################################################################
# API for Pin
################################################################

# return a specific pin by id(id, name, x, y, package_id)
@app.route('/api/pin/<int:pin_id>', methods=['GET'])
def get_pin(pin_id):
    pin = database_ipc.get_pin(g.session, pin_id)
    if not pin:
        return jsonify({"error": "Pin not found"}), 404

    return jsonify({
        "name": pin.name,
        "x": pin.x,
        "y": pin.y,
        "package_id": pin.package_id
    })

# return a list of all pins for a specific package (id, name, x, y)
@app.route('/api/pins/<int:package_id>', methods=['GET'])
def get_pins_by_package(package_id):
    pins = database_ipc.get_pins_by_package(g.session, package_id)
    return jsonify([
        {
            "id": pin.id,
            "name": pin.name,
            "x": pin.x,
            "y": pin.y,
        } for pin in pins
    ])

# create a new pin with name, package_id, optional x and y
@app.route('/api/pins', methods=['POST'])
def create_pin():
    data = request.json
    if not data or 'name' not in data or 'package_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        pin = database_ipc.create_pin(
            g.session,
            data['name'],
            data['package_id'],
            data.get('x'),
            data.get('y')
        )
        return jsonify({
            "id": pin.id,
            "name": pin.name,
            "x": pin.x,
            "y": pin.y,
            "package_id": pin.package_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing pin by id with optional name, x, y and package_id
@app.route('/api/pins/<int:pin_id>', methods=['PUT'])
def update_pin(pin_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_pin(
            g.session,
            pin_id,
            data.get('name'),
            data.get('x'),
            data.get('y'),
            data.get('package_id')
        )
        if not success:
            return jsonify({"error": "Pin not found"}), 404

        pin = database_ipc.get_pin(g.session, pin_id)
        return jsonify({
            "id": pin.id,
            "name": pin.name,
            "x": pin.x,
            "y": pin.y,
            "package_id": pin.package_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a pin by id only if it has no dependencies
@app.route('/api/pins/<int:pin_id>', methods=['DELETE'])
def delete_pin(pin_id):
    try:
        success, message = database_ipc.delete_pin(g.session, pin_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete pin" in message else 404
        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Pin by id (pin and all its dependencies)
@app.route('/api/pins/<int:pin_id>/deep-delete', methods=['DELETE'])
def deep_delete_pin_api(pin_id):
    try:
        success, message = database_ipc.deep_delete_pin(g.session, pin_id)
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        return jsonify({
            "message": message,
            "pin_id": pin_id,
            "operation": "deep_delete"
        }), 200
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    

################################################################
# API for Component
################################################################

# return a specific component by id (id, name, package_id, board_id, part, layer, rotation, x, y)
@app.route('/api/component/<int:component_id>', methods=['GET'])
def get_component(component_id):
    component = database_ipc.get_component(g.session, component_id)
    if not component:
        return jsonify({"error": "Component not found"}), 404

    return jsonify({
        "name": component.name,
        "package_id": component.package_id,
        "board_id": component.board_id,
        "part": component.part,
        "layer": component.layer,
        "rotation": component.rotation,
        "x": component.x,
        "y": component.y
    })

# return a list of all components for a specific board (id, name, package_id, board_id, part)
@app.route('/api/components/<int:board_id>', methods=['GET'])
def get_components_by_board(board_id):
    components = database_ipc.get_components_by_board(g.session, board_id)
    return jsonify([{
        "id": component.id,
        "name": component.name,
        "package_id": component.package_id,
        "board_id": component.board_id,
        "part": component.part,
    } for component in components])

# return a list of all components by board_id, include package and pin details
@app.route('/api/components/<int:board_id>/details', methods=['GET'])
def get_components_details_by_board(board_id):
    components = database_ipc.get_components_by_board(g.session, board_id)
    result = []

    for component in components:
        package = database_ipc.get_package(g.session, component.package_id)
        if not package:
            continue  # oppure puoi aggiungere un errore specifico per questo componente

        pins = database_ipc.get_pins_by_package(g.session, package.id)
        pins_info = [{
            "name": pin.name,
            "x": pin.x,
            "y": pin.y
        } for pin in pins]

        result.append({
            "component_info": {
                "id": component.id,
                "name": component.name,
                "part": component.part,
                "layer": component.layer,
                "rotation": component.rotation,
                "x": component.x,
                "y": component.y
            },
            "package_info": {
                "id": package.id,
                "polygon": package.polygon,
                "pins": pins_info
            }
        })

    return jsonify(result)

# return a specific component by id and include package and pin details
@app.route('/api/component/<int:component_id>/details', methods=['GET'])
def get_component_details(component_id):
    component = database_ipc.get_component(g.session, component_id)
    if not component:
        return jsonify({"error": "Component not found"}), 404

    package = database_ipc.get_package(g.session, component.package_id)
    if not package:
        return jsonify({"error": "Associated package not found"}), 404

    pins = database_ipc.get_pins_by_package(g.session, package.id)
    pins_info = [{
        "name": pin.name,
        "x": pin.x,
        "y": pin.y
    } for pin in pins]

    return jsonify({
        "component_info": {
            "name": component.name,
            "part": component.part,
            "layer": component.layer,
            "rotation": component.rotation,
            "x": component.x,
            "y": component.y
        },
        "package_info": {
            "polygon": package.polygon,
            "pins": pins_info
        }
    })

# create a new component with name, package_id, board_id, optional part, layer, rotation, x and y
@app.route('/api/components', methods=['POST'])
def create_component():
    data = request.json
    if not data or 'name' not in data or 'package_id' not in data or 'board_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        component = database_ipc.create_component(
            g.session,
            data['name'],
            data['package_id'],
            data['board_id'],
            data.get('part'),
            data.get('layer'),
            data.get('rotation'),
            data.get('x'),
            data.get('y')
        )
        return jsonify({
            "id": component.id,
            "name": component.name,
            "package_id": component.package_id,
            "board_id": component.board_id,
            "part": component.part,
            "layer": component.layer,
            "rotation": component.rotation,
            "x": component.x,
            "y": component.y
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing component by id with optional name, package_id, board_id, part, layer, rotation, x and y
@app.route('/api/components/<int:component_id>', methods=['PUT'])
def update_component(component_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_component(
            g.session,
            component_id,
            data.get('name'),
            data.get('package_id'),
            data.get('board_id'),
            data.get('part'),
            data.get('layer'),
            data.get('rotation'),
            data.get('x'),
            data.get('y')
        )
        if not success:
            return jsonify({"error": "Component not found"}), 404

        component = database_ipc.get_component(g.session, component_id)
        return jsonify({
            "id": component.id,
            "name": component.name,
            "package_id": component.package_id,
            "board_id": component.board_id,
            "part": component.part,
            "layer": component.layer,
            "rotation": component.rotation,
            "x": component.x,
            "y": component.y
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a component by id only if it has no dependencies
@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component_api(component_id):
    try:
        success, message = database_ipc.delete_component(g.session, component_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete component" in message else 404
        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Component by id (component and all its dependencies)
@app.route('/api/components/<int:component_id>/deep-delete', methods=['DELETE'])
def deep_delete_component_api(component_id):
    try:
        success, message = database_ipc.deep_delete_component(g.session, component_id)
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        return jsonify({
            "message": message,
            "component_id": component_id,
            "operation": "deep_delete"
        }), 200
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


################################################################
# API for Logical Net
################################################################

# return a specific logical_net by id (name, board_id)
@app.route('/api/logical_net/<int:logical_net_id>', methods=['GET'])
def get_logical_net(logical_net_id):
    logical_net = database_ipc.get_logical_net(g.session, logical_net_id)
    if not logical_net:
        return jsonify({"error": "Logical net not found"}), 404

    return jsonify({
        "name": logical_net.name,
        "board_id": logical_net.board_id
    })

# return a list of all logical_nets for a specific board (id, name)
@app.route('/api/logical_nets/<int:board_id>', methods=['GET'])
def get_logical_nets_by_board(board_id):
    logical_nets = database_ipc.get_logical_nets_by_board(g.session, board_id)
    return jsonify([{
        "id": net.id,
        "name": net.name
    } for net in logical_nets])

# create a new logical_net with name and board_id
@app.route('/api/logical_nets', methods=['POST'])
def create_logical_net():
    data = request.json
    if not data or 'name' not in data or 'board_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        logical_net = database_ipc.create_logical_net(
            g.session,
            data['name'],
            data['board_id']
        )
        return jsonify({
            "id": logical_net.id,
            "name": logical_net.name,
            "board_id": logical_net.board_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing logical_net by id with optional name and board_id
@app.route('/api/logical_nets/<int:logical_net_id>', methods=['PUT'])
def update_logical_net(logical_net_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_logical_net(
            g.session,
            logical_net_id,
            data.get('name'),
            data.get('board_id')
        )
        if not success:
            return jsonify({"error": "Logical net not found"}), 404

        logical_net = database_ipc.get_logical_net(g.session, logical_net_id)
        return jsonify({
            "id": logical_net.id,
            "name": logical_net.name,
            "board_id": logical_net.board_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a logical_net by id only if it has no dependencies
@app.route('/api/logical-nets/<int:logical_net_id>', methods=['DELETE'])
def delete_logical_net_api(logical_net_id):
    try:
        success, message = database_ipc.delete_logical_net(g.session, logical_net_id)
        if not success:
            return jsonify({"error": message}), 400 if "Cannot delete logical net" in message else 404
        return jsonify({"message": message})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Deep Delete Logical Net by id (logical_net and all its dependencies)
@app.route('/api/logical-nets/<int:logical_net_id>/deep-delete', methods=['DELETE'])
def deep_delete_logical_net_api(logical_net_id):
    try:
        success, message = database_ipc.deep_delete_logical_net(g.session, logical_net_id)
        if not success:
            return jsonify({"error": message}), 404 if "not found" in message else 500
        return jsonify({
            "message": message,
            "logical_net_id": logical_net_id,
            "operation": "deep_delete"
        }), 200
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


################################################################
# API for Net Pin
################################################################

# return a specific net pin by id (pin_id, component_id, logical_net_id)
@app.route('/api/net_pin/<int:net_pin_id>', methods=['GET'])
def get_net_pin(net_pin_id):
    net_pin = database_ipc.get_net_pin(g.session, net_pin_id)
    if not net_pin:
        return jsonify({"error": "Net pin not found"}), 404

    return jsonify({
        "id": net_pin.id,
        "pin_id": net_pin.pin_id,
        "component_id": net_pin.component_id,
        "logical_net_id": net_pin.logical_net_id
    })

# return a list of all net pins for a specific logical net (id, pin_id, component_id)
@app.route('/api/logical_net/<int:logical_net_id>/net_pins', methods=['GET'])
def get_net_pins_by_logical_net(logical_net_id):
    net_pins = database_ipc.get_net_pins_by_logical_net(g.session, logical_net_id)
    return jsonify([{
        "id": net_pin.id,
        "pin_id": net_pin.pin_id,
        "component_id": net_pin.component_id
    } for net_pin in net_pins])

# return a specific net pin by component_id and pin_id (logical_net_id)
@app.route('/api/component/<int:component_id>/pin/<int:pin_id>/net', methods=['GET'])
def get_net_by_component_pin(component_id, pin_id):
    net_pin = g.session.query(database_ipc.NetPin).filter_by(
        component_id=component_id, 
        pin_id=pin_id
    ).first()
    
    if not net_pin:
        return jsonify({"error": "No net connection found for this component-pin combination"}), 404
    
    return jsonify({
        "logical_net_id": net_pin.logical_net_id
    })

# return a list of all net pins for a specific component (pin_id, logical_net_id)
@app.route('/api/component/<int:component_id>/pin_nets', methods=['GET'])
def get_component_pin_nets(component_id):
    net_pins = database_ipc.get_net_pins_by_component(g.session, component_id)
    return jsonify([{
        "pin_id": net_pin.pin_id,
        "logical_net_id": net_pin.logical_net_id
    } for net_pin in net_pins])

# create a new net pin with component_id, pin_id and logical_net_id
@app.route('/api/net_pins', methods=['POST'])
def create_net_pin():
    data = request.json
    if not data or 'component_id' not in data or 'pin_id' not in data or 'logical_net_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        net_pin = database_ipc.create_net_pin(
            g.session,
            data['component_id'],
            data['pin_id'],
            data['logical_net_id']
        )
        return jsonify({
            "id": net_pin.id,
            "pin_id": net_pin.pin_id,
            "component_id": net_pin.component_id,
            "logical_net_id": net_pin.logical_net_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing net pin by id with optional component_id, pin_id and logical_net_id
@app.route('/api/net_pins/<int:net_pin_id>', methods=['PUT'])
def update_net_pin(net_pin_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        success = database_ipc.update_net_pin(
            g.session,
            net_pin_id,
            data.get('pin_id'),
            data.get('component_id'),
            data.get('logical_net_id')
        )
        if not success:
            return jsonify({"error": "Net pin not found"}), 404

        net_pin = database_ipc.get_net_pin(g.session, net_pin_id)
        return jsonify({
            "id": net_pin.id,
            "pin_id": net_pin.pin_id,
            "component_id": net_pin.component_id,
            "logical_net_id": net_pin.logical_net_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a net pin by id only if it has no dependencies
@app.route('/api/net_pins/<int:net_pin_id>', methods=['DELETE'])
def delete_net_pin(net_pin_id):
    try:
        success = database_ipc.delete_net_pin(g.session, net_pin_id)
        if not success:
            return jsonify({"error": "Net pin not found"}), 404

        return jsonify({"message": "Net pin deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500


################################################################
# API for info_txt
################################################################

# return a list of all info_txts for a specific board (id, board_id)
@app.route('/api/info_txts/<int:board_id>', methods=['GET'])
def get_info_txts_by_board(board_id):
    info_txts = database_ipc.get_info_txt_by_board(g.session, board_id)
    return jsonify([{
        "id": info.id,
        "board_id": info.board_id
    } for info in info_txts])

# return a specific info_txt by id (id, board_id, file_txt as base64)
@app.route('/api/info_txt/<int:info_txt_id>', methods=['GET'])
def get_info_txt_by_id(info_txt_id):
    info_txt = database_ipc.get_info_txt(g.session, info_txt_id)
    if not info_txt:
        return jsonify({"error": "Info text not found"}), 404

    file_txt_b64 = None
    if info_txt.file_txt:
        file_txt_b64 = base64.b64encode(info_txt.file_txt).decode('utf-8')

    return jsonify({
        "board_id": info_txt.board_id,
        "file_txt": file_txt_b64
    })

# create a new info_txt with file content and board_id
@app.route('/api/info_txt', methods=['POST'])
def create_info_txt():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    board_id = request.form.get('board_id')

    if not board_id:
        return jsonify({"error": "Missing board_id"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        board_id = int(board_id)
        file_content = file.read()
        info_txt = database_ipc.create_info_txt(g.session, board_id, file_content)

        return jsonify({
            "id": info_txt.id,
            "board_id": info_txt.board_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing info_txt by id with optional file content and board_id
@app.route('/api/info_txt/<int:info_txt_id>', methods=['PUT'])
def update_info_txt(info_txt_id):
    board_id = request.form.get('board_id')
    file = request.files.get('file')

    try:
        board_id = int(board_id) if board_id else None
        file_content = file.read() if file else None

        success = database_ipc.update_info_txt(
            g.session,
            info_txt_id,
            board_id,
            file_content
        )

        if not success:
            return jsonify({"error": "Info text not found"}), 404

        info_txt = database_ipc.get_info_txt(g.session, info_txt_id)
        return jsonify({
            "id": info_txt.id,
            "board_id": info_txt.board_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete an info_txt by id
@app.route('/api/info_txt/<int:info_txt_id>', methods=['DELETE'])
def delete_info_txt(info_txt_id):
    try:
        success = database_ipc.delete_info_txt(g.session, info_txt_id)
        if not success:
            return jsonify({"error": "Info text not found"}), 404

        return jsonify({"message": "Info text deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500


################################################################
# API for crop_schematic
################################################################

# return a list of all crop_schematics for a specific board (id, board_id)
@app.route('/api/crop_schematics/<int:board_id>', methods=['GET'])
def get_crop_schematics_by_board(board_id):
    crop_schematics = database_ipc.get_crop_schematic_by_board(g.session, board_id)
    return jsonify([{
        "id": crop.id,
        "board_id": crop.board_id
    } for crop in crop_schematics])

# return a specific crop_schematic by id (id, board_id, file_png as base64)
@app.route('/api/crop_schematic/<int:crop_schematic_id>', methods=['GET'])
def get_crop_schematic_by_id(crop_schematic_id):
    crop_schematic = database_ipc.get_crop_schematic(g.session, crop_schematic_id)
    if not crop_schematic:
        return jsonify({"error": "Crop schematic not found"}), 404

    file_png_b64 = None
    if crop_schematic.file_png:
        file_png_b64 = base64.b64encode(crop_schematic.file_png).decode('utf-8')

    return jsonify({
        "board_id": crop_schematic.board_id,
        "file_png": file_png_b64
    })

# create a new crop_schematic with file content and board_id
@app.route('/api/crop_schematic', methods=['POST'])
def create_crop_schematic():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    board_id = request.form.get('board_id')

    if not board_id:
        return jsonify({"error": "Missing board_id"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        board_id = int(board_id)
        file_content = file.read()
        crop_schematic = database_ipc.create_crop_schematic(g.session, board_id, file_content)

        return jsonify({
            "id": crop_schematic.id,
            "board_id": crop_schematic.board_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing crop_schematic by id with optional file content and board_id
@app.route('/api/crop_schematic/<int:crop_schematic_id>', methods=['PUT'])
def update_crop_schematic(crop_schematic_id):
    board_id = request.form.get('board_id')
    file = request.files.get('file')

    try:
        board_id = int(board_id) if board_id else None
        file_content = file.read() if file else None

        success = database_ipc.update_crop_schematic(
            g.session,
            crop_schematic_id,
            board_id,
            file_content
        )

        if not success:
            return jsonify({"error": "Crop schematic not found"}), 404

        crop_schematic = database_ipc.get_crop_schematic(g.session, crop_schematic_id)
        return jsonify({
            "id": crop_schematic.id,
            "board_id": crop_schematic.board_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a crop_schematic by id
@app.route('/api/crop_schematic/<int:crop_schematic_id>', methods=['DELETE'])
def delete_crop_schematic(crop_schematic_id):
    try:
        success = database_ipc.delete_crop_schematic(g.session, crop_schematic_id)
        if not success:
            return jsonify({"error": "Crop schematic not found"}), 404

        return jsonify({"message": "Crop schematic deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500


################################################################
# API for UserManual
################################################################

# return a list of all user manuals for a specific board (id, board_id)
@app.route('/api/user_manuals/<int:board_id>', methods=['GET'])
def get_user_manuals_by_board(board_id):
    user_manuals = database_ipc.get_user_manual_by_board(g.session, board_id)
    return jsonify([{
        "id": manual.id,
        "board_id": manual.board_id
    } for manual in user_manuals])

# return a specific user_manual by id (id, board_id, file_pdf as base64)
@app.route('/api/user_manual/<int:user_manual_id>', methods=['GET'])
def get_user_manual_by_id(user_manual_id):
    user_manual = database_ipc.get_user_manual(g.session, user_manual_id)
    if not user_manual:
        return jsonify({"error": "User manual not found"}), 404

    file_pdf_b64 = None
    if user_manual.file_pdf:
        file_pdf_b64 = base64.b64encode(user_manual.file_pdf).decode('utf-8')

    return jsonify({
        "board_id": user_manual.board_id,
        "file_pdf": file_pdf_b64
    })

# create a new user_manual with file content and board_id
@app.route('/api/user_manual', methods=['POST'])
def create_user_manual():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    board_id = request.form.get('board_id')

    if not board_id:
        return jsonify({"error": "Missing board_id"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        board_id = int(board_id)
        file_content = file.read()
        user_manual = database_ipc.create_user_manual(g.session, board_id, file_content)

        return jsonify({
            "id": user_manual.id,
            "board_id": user_manual.board_id
        }), 201
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# update an existing user_manual by id with optional file content and board_id
@app.route('/api/user_manual/<int:user_manual_id>', methods=['PUT'])
def update_user_manual(user_manual_id):
    board_id = request.form.get('board_id')
    file = request.files.get('file')

    try:
        board_id = int(board_id) if board_id else None
        file_content = file.read() if file else None

        success = database_ipc.update_user_manual(
            g.session,
            user_manual_id,
            board_id,
            file_content
        )

        if not success:
            return jsonify({"error": "User manual not found"}), 404

        user_manual = database_ipc.get_user_manual(g.session, user_manual_id)
        return jsonify({
            "id": user_manual.id,
            "board_id": user_manual.board_id
        })
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# delete a user_manual by id
@app.route('/api/user_manual/<int:user_manual_id>', methods=['DELETE'])
def delete_user_manual(user_manual_id):
    try:
        success = database_ipc.delete_user_manual(g.session, user_manual_id)
        if not success:
            return jsonify({"error": "User manual not found"}), 404

        return jsonify({"message": "User manual deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500
    

################################################################
# API for LLM 
################################################################

# Voice Assistance Route
@app.route('/api/voice-assistance/<int:board_id>', methods=['POST'])
def voice_assistance_route(board_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file sent"}), 400
    wav_file = request.files['file']
    if not wav_file.filename.lower().endswith('.wav'):
        return jsonify({"error": "The file must be a WAV"}), 400
    result = process_wav_file(wav_file, board_id)
    return jsonify(result)

# Text Assistance Route
@app.route('/api/text-assistance/<int:board_id>', methods=['POST'])
def text_assistance_route(board_id):
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    text_content = data.get('text', '').strip()
    if not text_content:
        return jsonify({"error": "No text provided"}), 400

    print(f"Processing text: {text_content}")

    result = process_query(text_content, board_id)

    if isinstance(result, dict):
        return jsonify(result)
    else:
        return jsonify({"error": "Unexpected response format from process_query.", "query": text_content, "components": []})

# Generate LLM data for a specific board
@app.route('/api/generate_llm_data/<int:board_id>', methods=['POST'])
def generate_llm_data(board_id):
    try:
        
        board = database_ipc.get_board(g.session, board_id)
        if not board:
            return jsonify({"error": f"Board with ID {board_id} not found"}), 404

        database_ipc.generate_logical_net_text("arboard.db", board_id)
        database_ipc.generate_component_list("arboard.db", board_id)

        info_txts = database_ipc.get_info_txt_by_board(g.session, board_id)

        return jsonify({
            "message": "LLM data generated successfully",
            "board_id": board_id,
            "info_txt_count": len(info_txts),
            "info_txt_ids": [info.id for info in info_txts]
        }), 200

    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500


################################################################
# API for general operations
################################################################

# Clear the entire database
@app.route('/api/clear-database', methods=['DELETE'])
def clear_database():
    try:
        success = database_ipc.clear_all_database(g.session)
        if success:
            return jsonify({"message": "Database cleared successfully"})
        else:
            return jsonify({"error": "Failed to clear database"}), 500
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# Upload IPC2581 file and parse it to populate the database
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            stats, board_id = parse_ipc2581_and_populate_db(filepath, g.session)
            return jsonify({
                'message': 'File uploaded and processed successfully',
                'board_id': board_id,
                'stats': stats
            }), 200
        except Exception as e:
            g.session.rollback()
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    return jsonify({'error': 'File type not allowed'}), 400

################################################################


# Run the Flask application for server IPC
if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5001, debug=False)