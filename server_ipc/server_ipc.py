from flask import Flask, request, jsonify, g
import database_ipc
from database_ipc import Session
import os
from werkzeug.utils import secure_filename
from read_IPC import parse_ipc2581_and_populate_db

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'cvg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inizializza il database
database_ipc.init_db()

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
    boards = database_ipc.get_all_boards(g.session)
    return jsonify([{
        "id": board.id,
        "name": board.name,
        "polygon": board.polygon
    } for board in boards])

@app.route('/api/boards/<int:board_id>', methods=['GET'])
def get_board(board_id):
    board = database_ipc.get_board(g.session, board_id)
    if not board:
        return jsonify({"error": "Board not found"}), 404

    return jsonify({
        "id": board.id,
        "name": board.name,
        "polygon": board.polygon
    })

@app.route('/api/boards/<int:board_id>/polygon', methods=['GET'])
def get_board_polygon(board_id):
    board = database_ipc.get_board(g.session, board_id)
    if not board:
        return jsonify({"error": "Board not found"}), 404

    return jsonify({
        "polygon": board.polygon
    })

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

@app.route('/api/boards/<int:board_id>', methods=['DELETE'])
def delete_board(board_id):
    try:
        success = database_ipc.delete_board(g.session, board_id)
        if not success:
            return jsonify({"error": "Board not found"}), 404

        return jsonify({"message": "Board deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Package
@app.route('/api/packages', methods=['GET'])
def get_packages():
    packages = database_ipc.get_all_packages(g.session)
    return jsonify([{
        "id": package.id,
        "name": package.name,
        "height": package.height,
        "polygon": package.polygon
    } for package in packages])

@app.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package(package_id):
    package = database_ipc.get_package(g.session, package_id)
    if not package:
        return jsonify({"error": "Package not found"}), 404

    return jsonify({
        "id": package.id,
        "name": package.name,
        "height": package.height,
        "polygon": package.polygon
    })

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

@app.route('/api/packages/<int:package_id>', methods=['DELETE'])
def delete_package(package_id):
    try:
        success = database_ipc.delete_package(g.session, package_id)
        if not success:
            return jsonify({"error": "Package not found"}), 404

        return jsonify({"message": "Package deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Pin
@app.route('/api/pins', methods=['GET'])
def get_pins():
    package_id = request.args.get('package_id', type=int)

    if package_id:
        pins = database_ipc.get_pins_by_package(g.session, package_id)
    else:
        # Questa potrebbe essere un'operazione costosa se ci sono molti pin
        pins = g.session.query(database_ipc.Pin).all()

    return jsonify([{
        "id": pin.id,
        "name": pin.name,
        "x": pin.x,
        "y": pin.y,
        "package_id": pin.package_id
    } for pin in pins])

@app.route('/api/pins/<int:pin_id>', methods=['GET'])
def get_pin(pin_id):
    pin = database_ipc.get_pin(g.session, pin_id)
    if not pin:
        return jsonify({"error": "Pin not found"}), 404

    return jsonify({
        "id": pin.id,
        "name": pin.name,
        "x": pin.x,
        "y": pin.y,
        "package_id": pin.package_id
    })

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

@app.route('/api/pins/<int:pin_id>', methods=['DELETE'])
def delete_pin(pin_id):
    try:
        success = database_ipc.delete_pin(g.session, pin_id)
        if not success:
            return jsonify({"error": "Pin not found"}), 404

        return jsonify({"message": "Pin deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Component
@app.route('/api/components', methods=['GET'])
def get_components():
    board_id = request.args.get('board_id', type=int)

    if board_id:
        components = database_ipc.get_components_by_board(g.session, board_id)
    else:
        components = g.session.query(database_ipc.Component).all()

    return jsonify([{
        "id": component.id,
        "name": component.name,
        "package_id": component.package_id,
        "board_id": component.board_id,
        "part": component.part,
        "layer": component.layer,
        "rotation": component.rotation,
        "x": component.x,
        "y": component.y
    } for component in components])

@app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    component = database_ipc.get_component(g.session, component_id)
    if not component:
        return jsonify({"error": "Component not found"}), 404

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

@app.route('/api/components/<int:component_id>/details', methods=['GET'])
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
    
@app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component(component_id):
    try:
        success = database_ipc.delete_component(g.session, component_id)
        if not success:
            return jsonify({"error": "Component not found"}), 404

        return jsonify({"message": "Component deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Logical Net
@app.route('/api/logical_nets', methods=['GET'])
def get_logical_nets():
    board_id = request.args.get('board_id', type=int)

    if board_id:
        logical_nets = database_ipc.get_logical_nets_by_board(g.session, board_id)
    else:
        logical_nets = g.session.query(database_ipc.LogicalNet).all()

    return jsonify([{
        "id": net.id,
        "name": net.name,
        "board_id": net.board_id
    } for net in logical_nets])

@app.route('/api/logical_nets/<int:logical_net_id>', methods=['GET'])
def get_logical_net(logical_net_id):
    logical_net = database_ipc.get_logical_net(g.session, logical_net_id)
    if not logical_net:
        return jsonify({"error": "Logical net not found"}), 404

    return jsonify({
        "id": logical_net.id,
        "name": logical_net.name,
        "board_id": logical_net.board_id
    })

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

@app.route('/api/logical_nets/<int:logical_net_id>', methods=['DELETE'])
def delete_logical_net(logical_net_id):
    try:
        success = database_ipc.delete_logical_net(g.session, logical_net_id)
        if not success:
            return jsonify({"error": "Logical net not found"}), 404

        return jsonify({"message": "Logical net deleted successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

# API per Net Pin
@app.route('/api/net_pins', methods=['GET'])
def get_net_pins():
    component_id = request.args.get('component_id', type=int)
    logical_net_id = request.args.get('logical_net_id', type=int)

    if component_id:
        net_pins = database_ipc.get_net_pins_by_component(g.session, component_id)
    elif logical_net_id:
        net_pins = database_ipc.get_net_pins_by_logical_net(g.session, logical_net_id)
    else:
        net_pins = g.session.query(database_ipc.NetPin).all()

    return jsonify([{
        "id": net_pin.id,
        "pin_id": net_pin.pin_id,
        "component_id": net_pin.component_id,
        "logical_net_id": net_pin.logical_net_id
    } for net_pin in net_pins])

@app.route('/api/net_pins/<int:net_pin_id>', methods=['GET'])
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

@app.route('/api/clear-database', methods=['DELETE'])
def clear_database():
    try:
        database_ipc.clear_all_database(g.session)
        return jsonify({"message": "database cleared successfully"})
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# Specify function 

@app.route('/api/logical_nets/<int:net_id>/pins', methods=['GET'])
def get_pins_by_net(net_id):
    try:
        # Verifica che la rete logica esista
        logical_net = database_ipc.get_logical_net(g.session, net_id)
        if not logical_net:
            return jsonify({"error": "Logical net not found"}), 404

        # Ottieni tutte le connessioni net_pin per questa rete
        net_pins = database_ipc.get_net_pins_by_logical_net(g.session, net_id)

        # Prepara la risposta con i dettagli dei pin e dei componenti
        result = []
        for net_pin in net_pins:
            # Ottieni i dettagli del pin
            pin = database_ipc.get_pin(g.session, net_pin.pin_id)
            # Ottieni i dettagli del componente
            component = database_ipc.get_component(g.session, net_pin.component_id)

            if pin and component:
                result.append({
                    "pin": {
                        "id": pin.id,
                        "name": pin.name,
                        "x": pin.x,
                        "y": pin.y
                    },
                    "component": {
                        "id": component.id,
                        "name": component.name,
                        "part": component.part,
                        "layer": component.layer
                    }
                })

        return jsonify({
            "pins": result
        })

    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/components/<string:component_name>/pins/<string:pin_name>/net', methods=['GET'])
def get_net_by_component_and_pin_api(component_name, pin_name):
    board_id = request.args.get('board_id', type=int)
    try:
        net = database_ipc.get_net_by_component_and_pin(g.session, component_name, pin_name, board_id)
        if net is None:
            return jsonify({"error": f"No net found for component '{component_name}' and pin '{pin_name}'"}), 404
        return jsonify(net)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/nets/by-name/<string:net_name>', methods=['GET'])
def get_logical_net_by_name_api(net_name):
    board_id = request.args.get('board_id', type=int)
    try:
        net = database_ipc.get_logical_net_by_name(g.session, net_name, board_id)
        if net is None:
            return jsonify({"error": f"Net with name '{net_name}' not found"}), 404
        return jsonify({
            "id": net.id,
            "name": net.name,
            "board_id": net.board_id
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.session.rollback()
        return jsonify({"error": str(e)}), 500
    
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
            result = parse_ipc2581_and_populate_db(filepath, g.session)
            return jsonify({
                'message': 'File uploaded and processed successfully',
                'stats': result
            }), 200
        except Exception as e:
            g.session.rollback()
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    return jsonify({'error': 'File type not allowed'}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)