import xml.etree.ElementTree as ET
import json
import database_ipc
from database_ipc import Session

def parse_ipc2581_and_populate_db(file_path, session=None):
    if session is None:
        database_ipc.init_db()
        session = Session()
        close_session = True
    else:
        close_session = False

    try:
        # Parse the XML file
        namespaces = {'ipc': 'http://webstds.ipc.org/2581'}
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Create board
        step_ref_elem = root.find('.//ipc:StepRef', namespaces)
        if step_ref_elem is None or step_ref_elem.text is None:
            raise ValueError("StepRef non trovato nel file IPC-2581.")
        step_ref = step_ref_elem.text

        step_elem = root.find('.//ipc:Step[@name="' + step_ref + '"]', namespaces)
        if step_elem is None:
            raise ValueError(f'Step con nome "{step_ref}" non trovato nel file IPC-2581.')

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
        board = database_ipc.create_board(session, step_ref, board_polygon)
        board_id = board.id

        # Process packages
        packages = {}  # Store package_id by name for later reference

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

        # Process components
        components = {}  # Store component_id by refDes for later reference

        for component_elem in root.findall('.//ipc:Component', namespaces):
            ref_des = component_elem.get('refDes')
            package_ref = component_elem.get('packageRef')
            layer_ref = component_elem.get('layerRef')
            part = component_elem.get('part', '')  # Estrai l'attributo part

            # Get component location and rotation
            location_elem = component_elem.find('.//ipc:Location', namespaces)
            x = float(location_elem.get('x', '0.0')) if location_elem is not None else 0.0
            y = float(location_elem.get('y', '0.0')) if location_elem is not None else 0.0

            xform_elem = component_elem.find('.//ipc:Xform', namespaces)
            rotation = float(xform_elem.get('rotation', '0.0')) if xform_elem is not None else 0.0

            # Map layer to TOP or BOTTOM
            layer = 'TOP' if layer_ref == 'TOP' else 'BOTTOM'

            if package_ref in packages:
                component = database_ipc.create_component(
                    session,
                    ref_des,
                    packages[package_ref],
                    board_id,
                    part,  # Passa il valore part
                    layer,
                    int(rotation),
                    x,
                    y
                )
                components[ref_des] = component.id

        # Process logical nets
        nets = {}  # Store net_id by name for later reference

        for net_elem in root.findall('.//ipc:LogicalNet', namespaces):
            net_name = net_elem.get('name')
            net = database_ipc.create_logical_net(session, net_name, board_id)
            nets[net_name] = net.id

        # Process net pins
        for net_pin_elem in net_elem.findall('.//ipc:LogicalNetPin', namespaces):
            pin_number = net_pin_elem.get('pin')
            component_ref = net_pin_elem.get('componentRef')

            if component_ref in components:
                component_id = components[component_ref]

                # Find the pin_id for this component and pin number
                # This requires a query to find the pin in the package associated with this component
                component = session.query(database_ipc.Component).filter_by(id=component_id).first()
                if component:
                    pins = session.query(database_ipc.Pin).filter_by(package_id=component.package_id).all()
                    for pin in pins:
                        if pin.name == pin_number or str(pin.id) == pin_number:
                            # Check if this connection already exists before creating it
                            existing = session.query(database_ipc.NetPin).filter_by(
                                component_id=component_id,
                                pin_id=pin.id,
                                logical_net_id=net.id
                            ).first()

                            if not existing:
                                database_ipc.create_net_pin(session, component_id, pin.id, net.id)
                                break

        result = {
            "board_count": 1,
            "package_count": len(packages),
            "component_count": len(components),
            "net_count": len(nets)
        }

        # Commit changes if we created our own session
        if close_session:
            session.commit()
            session.close()

        return result

    except Exception as e:
        # Rollback in case of error
        if close_session:
            session.rollback()
            session.close()
        raise e
        
# Example usage
if __name__ == "__main__":
    result = parse_ipc2581_and_populate_db("server_ipc/testcase3.cvg")
    print(result)
