import xml.etree.ElementTree as ET
import json
import database_ipc
from database_ipc import Session
import logging

# Configurazione del logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_ipc2581_and_populate_db(file_path, session=None):
    if session is None:
        database_ipc.init_db()
        session = Session()
        close_session = True
    else:
        close_session = False

    try:
        logger.info(f"Parsing file: {file_path}")
        # Parse the XML file
        namespaces = {'ipc': 'http://webstds.ipc.org/2581'}
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Create board
        step_ref_elem = root.find('.//ipc:StepRef', namespaces)
        board_name = None

        if step_ref_elem is not None and step_ref_elem.text is not None:
            step_ref = step_ref_elem.text
            step_elem = root.find(f'.//ipc:Step[@name="{step_ref}"]', namespaces)
            board_name = step_ref
        else:
            # Fallback: use the first Step element or a default name
            step_elem = root.find('.//ipc:Step', namespaces)
            if step_elem is not None:
                board_name = step_elem.get('name', 'Unknown Board')
            else:
                board_name = "Unknown Board"
                step_elem = None
                logger.warning("StepRef non trovato nel file IPC-2581. Usando nome predefinito.")

        # Extract board polygon data
        board_polygon = None
        if step_elem is not None:
            profile_elem = step_elem.find('.//ipc:Profile', namespaces)
            if profile_elem is not None:
                polygon_elem = profile_elem.find('.//ipc:Polygon', namespaces)
                if polygon_elem is not None:
                    # Serialize polygon data as JSON
                    polygon_points = []

                    # Extract all polygon points
                    for point_elem in polygon_elem:
                        point_type = point_elem.tag.split('}')[-1]  # Remove namespace
                        x = float(point_elem.get('x', '0.0'))
                        y = float(point_elem.get('y', '0.0'))

                        point_data = {
                            'type': point_type,
                            'x': x,
                            'y': y
                        }

                        # Add curve-specific attributes if present
                        if point_type == 'PolyStepCurve':
                            center_x = float(point_elem.get('centerX', '0.0'))
                            center_y = float(point_elem.get('centerY', '0.0'))
                            clockwise = point_elem.get('clockwise', 'FALSE') == 'TRUE'
                            point_data.update({
                                'centerX': center_x,
                                'centerY': center_y,
                                'clockwise': clockwise
                            })

                        polygon_points.append(point_data)

                    board_polygon = json.dumps(polygon_points)

        # Create board with polygon data
        board = database_ipc.create_board(session, board_name, board_polygon)
        board_id = board.id

        # Process packages
        packages = {}  # Store package_id by name for later reference
        package_count = 0

        for package_elem in root.findall('.//ipc:Package', namespaces):
            name = package_elem.get('name')
            height = float(package_elem.get('height', '0.0'))

            # Extract polygon data if available
            polygon = None
            outline_elem = package_elem.find('.//ipc:Outline', namespaces)
            if outline_elem is not None:
                polygon_elem = outline_elem.find('.//ipc:Polygon', namespaces)
                if polygon_elem is not None:
                    # Serialize polygon data as JSON
                    polygon_points = []

                    # Extract all polygon points
                    for point_elem in polygon_elem:
                        point_type = point_elem.tag.split('}')[-1]  # Remove namespace
                        x = float(point_elem.get('x', '0.0'))
                        y = float(point_elem.get('y', '0.0'))

                        point_data = {
                            'type': point_type,
                            'x': x,
                            'y': y
                        }

                        # Add curve-specific attributes if present
                        if point_type == 'PolyStepCurve':
                            center_x = float(point_elem.get('centerX', '0.0'))
                            center_y = float(point_elem.get('centerY', '0.0'))
                            clockwise = point_elem.get('clockwise', 'FALSE') == 'TRUE'
                            point_data.update({
                                'centerX': center_x,
                                'centerY': center_y,
                                'clockwise': clockwise
                            })

                        polygon_points.append(point_data)

                    polygon = json.dumps(polygon_points)

            package = database_ipc.create_package(session, name, height, polygon)
            packages[name] = package.id
            package_count += 1

            # Process pins for this package
            for pin_elem in package_elem.findall('.//ipc:Pin', namespaces):
                pin_number = pin_elem.get('number')
                pin_name = pin_elem.get('name', '')

                # Get pin location
                location_elem = pin_elem.find('.//ipc:Location', namespaces)
                if location_elem is not None:
                    x = float(location_elem.get('x', '0.0'))
                    y = float(location_elem.get('y', '0.0'))

                database_ipc.create_pin(session, pin_name or pin_number, package.id, x, y)

        logger.info(f"Estratti {package_count} package")

        # Process components
        components = {}  # Store component_id by refDes for later reference
        component_count = 0

        # Cerca componenti sia nel tag Component che nei BomItem/RefDes
        for component_elem in root.findall('.//ipc:Component', namespaces):
            ref_des = component_elem.get('refDes')
            package_ref = component_elem.get('packageRef')
            layer_ref = component_elem.get('layerRef', 'Top Layer')
            part = component_elem.get('part', '')

            # Get component location and rotation
            location_elem = component_elem.find('.//ipc:Location', namespaces)
            x = float(location_elem.get('x', '0.0')) if location_elem is not None else 0.0
            y = float(location_elem.get('y', '0.0')) if location_elem is not None else 0.0

            xform_elem = component_elem.find('.//ipc:Xform', namespaces)
            rotation = float(xform_elem.get('rotation', '0.0')) if xform_elem is not None else 0.0

            # Map layer to TOP or BOTTOM
            layer = 'TOP' if 'top' in layer_ref.lower() else 'BOTTOM'

            if package_ref in packages:
                component = database_ipc.create_component(
                    session,
                    ref_des,
                    packages[package_ref],
                    board_id,
                    part,
                    layer,
                    int(rotation),
                    x,
                    y
                )
                components[ref_des] = component.id
                component_count += 1

        # Cerca anche nei BomItem/RefDes
        for bom_item in root.findall('.//ipc:BomItem', namespaces):
            for ref_des_elem in bom_item.findall('.//ipc:RefDes', namespaces):
                ref_des = ref_des_elem.get('name')
                package_ref = ref_des_elem.get('packageRef')
                layer_ref = ref_des_elem.get('layerRef', 'Top Layer')
                part = bom_item.get('description', '')

                # Se il componente è già stato creato, salta
                if ref_des in components:
                    continue

                # Map layer to TOP or BOTTOM
                layer = 'TOP' if 'top' in layer_ref.lower() else 'BOTTOM'

                if package_ref in packages:
                    component = database_ipc.create_component(
                        session,
                        ref_des,
                        packages[package_ref],
                        board_id,
                        part,
                        layer,
                        0,  # Rotation default
                        0.0,  # X default
                        0.0   # Y default
                    )
                    components[ref_des] = component.id
                    component_count += 1

        logger.info(f"Estratti {component_count} componenti")

        # Process logical nets
        nets = {}  # Store net_id by name for later reference
        net_count = 0

        # Metodo 1: Estrai reti dai tag LogicalNet
        for net_elem in root.findall('.//ipc:LogicalNet', namespaces):
            net_name = net_elem.get('name')
            net = database_ipc.create_logical_net(session, net_name, board_id)
            nets[net_name] = net.id
            net_count += 1

        # Metodo 2: Estrai reti dagli attributi net dei PadStack
        for padstack in root.findall('.//ipc:PadStack', namespaces):
            net_name = padstack.get('net')
            if net_name and net_name != "No Net" and net_name not in nets:
                net = database_ipc.create_logical_net(session, net_name, board_id)
                nets[net_name] = net.id
                net_count += 1

        logger.info(f"Estratte {net_count} reti logiche")

        # Process net pins - Metodo 1: dai LogicalNetPin
        net_pin_count = 0
        for net_elem in root.findall('.//ipc:LogicalNet', namespaces):
            net_name = net_elem.get('name')
            if net_name not in nets:
                continue

            net_id = nets[net_name]

            for net_pin_elem in net_elem.findall('.//ipc:LogicalNetPin', namespaces):
                pin_number = net_pin_elem.get('pin')
                component_ref = net_pin_elem.get('componentRef')

                if component_ref in components:
                    component_id = components[component_ref]

                    # Find the pin_id for this component and pin number
                    component = session.query(database_ipc.Component).filter_by(id=component_id).first()
                    if component:
                        pins = session.query(database_ipc.Pin).filter_by(package_id=component.package_id).all()
                        for pin in pins:
                            if pin.name == pin_number or str(pin.id) == pin_number:
                                # Check if this connection already exists before creating it
                                existing = session.query(database_ipc.NetPin).filter_by(
                                    component_id=component_id,
                                    pin_id=pin.id,
                                    logical_net_id=net_id
                                ).first()

                                if not existing:
                                    database_ipc.create_net_pin(session, component_id, pin.id, net_id)
                                    net_pin_count += 1
                                break

        logger.info(f"Collegate {net_pin_count} connessioni pin-net tradizionali")

        # Process net pins - Metodo 2: dai PadStack con attributo net e PinRef
        padstack_net_pin_count = 0

        for padstack in root.findall('.//ipc:PadStack', namespaces):
            net_name = padstack.get('net')
            if not net_name or net_name == "No Net" or net_name not in nets:
                continue

            net_id = nets[net_name]

            # Cerca tutti i PinRef all'interno di questo PadStack
            for layer_pad in padstack.findall('.//ipc:LayerPad', namespaces):
                for pin_ref in layer_pad.findall('.//ipc:PinRef', namespaces):
                    component_ref = pin_ref.get('componentRef')
                    pin_number = pin_ref.get('pin')

                    if component_ref in components:
                        component_id = components[component_ref]

                        # Trova il pin corrispondente
                        component = session.query(database_ipc.Component).filter_by(id=component_id).first()
                        if component:
                            pins = session.query(database_ipc.Pin).filter_by(package_id=component.package_id).all()
                            for pin in pins:
                                if pin.name == pin_number or str(pin.id) == pin_number:
                                    # Verifica se la connessione esiste già
                                    existing = session.query(database_ipc.NetPin).filter_by(
                                        component_id=component_id,
                                        pin_id=pin.id,
                                        logical_net_id=net_id
                                    ).first()

                                    if not existing:
                                        database_ipc.create_net_pin(session, component_id, pin.id, net_id)
                                        padstack_net_pin_count += 1
                                    break

        logger.info(f"Collegate {padstack_net_pin_count} connessioni pin-net da PadStack")

        result = {
            "board_count": 1,
            "package_count": package_count,
            "component_count": component_count,
            "net_count": net_count,
            "net_pin_count": net_pin_count + padstack_net_pin_count
        }

        logger.info(f"Parsing completato con successo: {result}")

        # Commit changes if we created our own session
        if close_session:
            session.commit()
            session.close()

        return result

    except Exception as e:
        # Rollback in case of error
        logger.error(f"Errore durante il parsing: {str(e)}", exc_info=True)
        if close_session:
            session.rollback()
            session.close()
        raise e

# Example usage
if __name__ == "__main__":
    result = parse_ipc2581_and_populate_db("server_ipc/testcase3.cvg")
    print(result)