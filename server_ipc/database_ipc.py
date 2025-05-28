from sqlalchemy import create_engine, Column, Text, Integer, String, Float, ForeignKey, CheckConstraint, LargeBinary, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import sqlite3

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///arboard.db')
Session = sessionmaker(bind=engine)

# Models defined
class Board(Base):
    __tablename__ = 'board'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    polygon = Column(Text)

    components = relationship("Component", back_populates="board")
    logical_nets = relationship("LogicalNet", back_populates="board")

class Package(Base):
    __tablename__ = 'package'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    height = Column(Float, nullable=True)
    polygon = Column(Text)

    pins = relationship("Pin", back_populates="package")
    components = relationship("Component", back_populates="package")

class Pin(Base):
    __tablename__ = 'pin'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    package_id = Column(Integer, ForeignKey('package.id'))

    package = relationship("Package", back_populates="pins")
    net_connections = relationship("NetPin", back_populates="pin")

class Component(Base):
    __tablename__ = 'component'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    package_id = Column(Integer, ForeignKey('package.id'))
    board_id = Column(Integer, ForeignKey('board.id'))
    layer = Column(Enum('TOP', 'BOTTOM', name='layer_types'), nullable=True)
    part = Column(String, nullable=True)
    rotation = Column(Integer, nullable=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)

    package = relationship("Package", back_populates="components")
    board = relationship("Board", back_populates="components")
    net_connections = relationship("NetPin", back_populates="component")

class LogicalNet(Base):
    __tablename__ = 'logical_net'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    board_id = Column(Integer, ForeignKey('board.id'))

    board = relationship("Board", back_populates="logical_nets")
    pin_connections = relationship("NetPin", back_populates="logical_net")

class NetPin(Base):
    __tablename__ = 'net_pin'
    id = Column(Integer, primary_key=True)
    pin_id = Column(Integer, ForeignKey('pin.id'))
    component_id = Column(Integer, ForeignKey('component.id'))
    logical_net_id = Column(Integer, ForeignKey('logical_net.id'))

    pin = relationship("Pin", back_populates="net_connections")
    component = relationship("Component", back_populates="net_connections")
    logical_net = relationship("LogicalNet", back_populates="pin_connections")

class InfoTxt(Base):
    __tablename__ = 'info_txt'
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('board.id'))
    file_txt = Column(LargeBinary)
    
    board = relationship("Board")

class CropSchematic(Base):
    __tablename__ = 'crop_schematic'
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('board.id'))
    file_png = Column(LargeBinary)
    
    board = relationship("Board")

class UserManual(Base):
    __tablename__ = 'user_manual'
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('board.id'))
    file_pdf = Column(LargeBinary)
    
    board = relationship("Board")


# Database init
def init_db():
    Base.metadata.create_all(engine)

# CREATE operations
def create_board(session, name, polygon=None):
    board = Board(name=name, polygon=polygon)
    session.add(board)
    session.commit()
    return board

def create_package(session, name, height=None, polygon=None):
    package = Package(name=name, height=height, polygon=polygon)
    session.add(package)
    session.commit()
    return package

def create_pin(session, name, package_id, x=None, y=None):
    pin = Pin(name=name, x=x, y=y, package_id=package_id)
    session.add(pin)
    session.commit()
    return pin

def create_component(session, name, package_id, board_id, part=None, layer=None, rotation=None, x=None, y=None):
    component = Component(
        name=name,
        package_id=package_id,
        board_id=board_id,
        part=part,
        layer=layer,
        rotation=rotation,
        x=x,
        y=y
    )
    session.add(component)
    session.commit()
    return component

def create_logical_net(session, name, board_id):
    logical_net = LogicalNet(name=name, board_id=board_id)
    session.add(logical_net)
    session.commit()
    return logical_net

def create_net_pin(session, component_id, pin_id, logical_net_id):
    # Verifica se la connessione esiste già
    existing = session.query(NetPin).filter_by(
        pin_id=pin_id,
        component_id=component_id
    ).first()

    if not existing:
        # Solo se non esiste, crea una nuova connessione
        net_pin = NetPin(pin_id=pin_id, component_id=component_id, logical_net_id=logical_net_id)
        session.add(net_pin)
        session.commit()
        return net_pin
    else:
        print(f"Connection already exists: {existing.pin_id} -> {existing.component_id}")
        
        '''# Aggiorna la rete logica se necessario
        if existing.logical_net_id != logical_net_id:
            existing.logical_net_id = logical_net_id
            session.commit()
        return existing'''

# READ operations
def get_board(session, board_id):
    return session.query(Board).filter_by(id=board_id).first()

def get_all_boards(session):
    return session.query(Board).all()

def get_package(session, package_id):
    return session.query(Package).filter_by(id=package_id).first()

def get_all_packages(session):
    return session.query(Package).all()

def get_pin(session, pin_id):
    return session.query(Pin).filter_by(id=pin_id).first()

def get_pins_by_package(session, package_id):
    return session.query(Pin).filter_by(package_id=package_id).all()

def get_component(session, component_id):
    return session.query(Component).filter_by(id=component_id).first()

def get_components_by_board(session, board_id):
    return session.query(Component).filter_by(board_id=board_id).all()

def get_logical_net(session, logical_net_id):
    return session.query(LogicalNet).filter_by(id=logical_net_id).first()

def get_logical_nets_by_board(session, board_id):
    return session.query(LogicalNet).filter_by(board_id=board_id).all()

def get_net_pin(session, net_pin_id):
    return session.query(NetPin).filter_by(id=net_pin_id).first()

def get_net_pins_by_component(session, component_id):
    return session.query(NetPin).filter_by(component_id=component_id).all()

def get_net_pins_by_logical_net(session, logical_net_id):
    return session.query(NetPin).filter_by(logical_net_id=logical_net_id).all()

# UPDATE operations
def update_board(session, board_id, name=None, polygon=None):
    board = session.query(Board).filter_by(id=board_id).first()
    if not board:
        return False

    if name is not None:
        board.name = name
    if polygon is not None:
        board.polygon = polygon

    session.commit()
    return True

def update_package(session, package_id, name=None, height=None, polygon=None):
    package = session.query(Package).filter_by(id=package_id).first()
    if not package:
        return False

    if name is not None:
        package.name = name
    if height is not None:
        package.height = height
    if polygon is not None:
        package.polygon = polygon

    session.commit()
    return True

def update_pin(session, pin_id, name=None, x=None, y=None, package_id=None):
    pin = session.query(Pin).filter_by(id=pin_id).first()
    if not pin:
        return False

    if name is not None:
        pin.name = name
    if x is not None:
        pin.x = x
    if y is not None:
        pin.y = y
    if package_id is not None:
        pin.package_id = package_id

    session.commit()
    return True

def update_component(session, component_id, name=None, package_id=None, board_id=None,
                    part=None, layer=None, rotation=None, x=None, y=None):
    component = session.query(Component).filter_by(id=component_id).first()
    if not component:
        return False

    if name is not None:
        component.name = name
    if package_id is not None:
        component.package_id = package_id
    if board_id is not None:
        component.board_id = board_id
    if part is not None:
        component.part = part
    if layer is not None:
        component.layer = layer
    if rotation is not None:
        component.rotation = rotation
    if x is not None:
        component.x = x
    if y is not None:
        component.y = y

    session.commit()
    return True

def update_logical_net(session, logical_net_id, name=None, board_id=None):
    logical_net = session.query(LogicalNet).filter_by(id=logical_net_id).first()
    if not logical_net:
        return False

    if name is not None:
        logical_net.name = name
    if board_id is not None:
        logical_net.board_id = board_id

    session.commit()
    return True

def update_net_pin(session, net_pin_id, pin_id=None, component_id=None, logical_net_id=None):
    net_pin = session.query(NetPin).filter_by(id=net_pin_id).first()
    if not net_pin:
        return False

    if pin_id is not None:
        net_pin.pin_id = pin_id
    if component_id is not None:
        net_pin.component_id = component_id
    if logical_net_id is not None:
        net_pin.logical_net_id = logical_net_id

    session.commit()
    return True

# DELETE operations
def delete_board(session, board_id):
    board = session.query(Board).filter_by(id=board_id).first()
    if not board:
        return False

    session.delete(board)
    session.commit()
    return True

def delete_package(session, package_id):
    package = session.query(Package).filter_by(id=package_id).first()
    if not package:
        return False

    session.delete(package)
    session.commit()
    return True

def delete_pin(session, pin_id):
    pin = session.query(Pin).filter_by(id=pin_id).first()
    if not pin:
        return False

    session.delete(pin)
    session.commit()
    return True

def delete_component(session, component_id):
    component = session.query(Component).filter_by(id=component_id).first()
    if not component:
        return False

    session.delete(component)
    session.commit()
    return True

def delete_logical_net(session, logical_net_id):
    logical_net = session.query(LogicalNet).filter_by(id=logical_net_id).first()
    if not logical_net:
        return False

    session.delete(logical_net)
    session.commit()
    return True

def delete_net_pin(session, net_pin_id):
    net_pin = session.query(NetPin).filter_by(id=net_pin_id).first()
    if not net_pin:
        return False

    session.delete(net_pin)
    session.commit()
    return True

def clear_all_database(session):
    # Elimina prima le associazioni (tabelle di join)
    session.query(NetPin).delete()

    # Poi elimina le entità principali
    session.query(Component).delete()
    session.query(Pin).delete()
    session.query(LogicalNet).delete()
    session.query(Package).delete()
    session.query(Board).delete()

    session.commit()
    return True

# Special functions

def get_logical_net_by_name(session, net_name, board_id=None):

    query = session.query(LogicalNet).filter(LogicalNet.name == net_name)

    if board_id is not None:
        query = query.filter(LogicalNet.board_id == board_id)

    nets = query.all()

    if not nets:
        return None
    elif len(nets) > 1:
        raise ValueError(f"Multiple nets found with name '{net_name}'")
    else:
        return nets[0]
    
def get_pins_by_net_name(session, net_name, board_id=None):
    try:
        net = get_logical_net_by_name(session, net_name, board_id)
        if not net:
            return None
        net_pins = session.query(NetPin).filter(NetPin.logical_net_id == net.id).all()

        result = []
        for net_pin in net_pins:
            component = session.query(Component).filter(Component.id == net_pin.component_id).first()
            pin = session.query(Pin).filter(Pin.id == net_pin.pin_id).first()
            if component and pin:
                result.append({
                    "component_id": component.id,
                    "component_name": component.name,
                    "pin_id": pin.id,
                    "pin_name": pin.name
                })
        return result
    except ValueError as e:
        raise e
    
def get_component_by_name(session, component_name, board_id=None):
    query = session.query(Component).filter(Component.name == component_name)
    if board_id is not None:
        query = query.filter(Component.board_id == board_id)
    components = query.all()
    if not components:
        return None
    elif len(components) > 1:
        raise ValueError(f"Multiple components found with name '{component_name}'")
    else:
        return components[0]
    
def get_pin_by_name_and_package(session, pin_name, package_id):
    pins = session.query(Pin).filter(Pin.name == pin_name, Pin.package_id == package_id).all()
    if not pins:
        return None
    elif len(pins) > 1:
        raise ValueError(f"Multiple pins found with name '{pin_name}' in package {package_id}")
    else:
        return pins[0]

def get_net_by_component_and_pin(session, component_name, pin_name, board_id=None):
    try:
        component = get_component_by_name(session, component_name, board_id)
        if not component:
            return None
        package = session.query(Package).filter(Package.id == component.package_id).first()
        if not package:
            return None
        pin = get_pin_by_name_and_package(session, pin_name, package.id)
        if not pin:
            return None
        net_pin = session.query(NetPin).filter(
            NetPin.component_id == component.id,
            NetPin.pin_id == pin.id
        ).first()

        if not net_pin:
            return None
        logical_net = session.query(LogicalNet).filter(LogicalNet.id == net_pin.logical_net_id).first()
        if logical_net:
            return {
                "net_id": logical_net.id,
                "net_name": logical_net.name,
                "board_id": logical_net.board_id
            }
        else:
            return None
    except ValueError as e:
        raise e
    


# To fix the position of this function 



def create_info_txt(session, board_id, file_txt):
    info_txt = InfoTxt(board_id=board_id, file_txt=file_txt)
    session.add(info_txt)
    session.commit()
    return info_txt

def create_crop_schematic(session, board_id, file_png):
    crop_schematic = CropSchematic(board_id=board_id, file_png=file_png)
    session.add(crop_schematic)
    session.commit()
    return crop_schematic

def create_user_manual(session, board_id, file_pdf):
    user_manual = UserManual(board_id=board_id, file_pdf=file_pdf)
    session.add(user_manual)
    session.commit()
    return user_manual

# READ operations per le nuove classi
def get_info_txt(session, info_txt_id):
    return session.query(InfoTxt).filter_by(id=info_txt_id).first()

def get_info_txt_by_board(session, board_id):
    return session.query(InfoTxt).filter_by(board_id=board_id).all()

def get_crop_schematic(session, crop_schematic_id):
    return session.query(CropSchematic).filter_by(id=crop_schematic_id).first()

def get_crop_schematic_by_board(session, board_id):
    return session.query(CropSchematic).filter_by(board_id=board_id).all()

def get_user_manual(session, user_manual_id):
    return session.query(UserManual).filter_by(id=user_manual_id).first()

def get_user_manual_by_board(session, board_id):
    return session.query(UserManual).filter_by(board_id=board_id).all()

# UPDATE operations per le nuove classi
def update_info_txt(session, info_txt_id, board_id=None, file_txt=None):
    info_txt = session.query(InfoTxt).filter_by(id=info_txt_id).first()
    if not info_txt:
        return False

    if board_id is not None:
        info_txt.board_id = board_id
    if file_txt is not None:
        info_txt.file_txt = file_txt

    session.commit()
    return True

def update_crop_schematic(session, crop_schematic_id, board_id=None, file_png=None):
    crop_schematic = session.query(CropSchematic).filter_by(id=crop_schematic_id).first()
    if not crop_schematic:
        return False

    if board_id is not None:
        crop_schematic.board_id = board_id
    if file_png is not None:
        crop_schematic.file_png = file_png

    session.commit()
    return True

def update_user_manual(session, user_manual_id, board_id=None, file_pdf=None):
    user_manual = session.query(UserManual).filter_by(id=user_manual_id).first()
    if not user_manual:
        return False

    if board_id is not None:
        user_manual.board_id = board_id
    if file_pdf is not None:
        user_manual.file_pdf = file_pdf

    session.commit()
    return True

# DELETE operations per le nuove classi
def delete_info_txt(session, info_txt_id):
    info_txt = session.query(InfoTxt).filter_by(id=info_txt_id).first()
    if not info_txt:
        return False

    session.delete(info_txt)
    session.commit()
    return True

def delete_crop_schematic(session, crop_schematic_id):
    crop_schematic = session.query(CropSchematic).filter_by(id=crop_schematic_id).first()
    if not crop_schematic:
        return False

    session.delete(crop_schematic)
    session.commit()
    return True

def delete_user_manual(session, user_manual_id):
    user_manual = session.query(UserManual).filter_by(id=user_manual_id).first()
    if not user_manual:
        return False

    session.delete(user_manual)
    session.commit()
    return True

#LLM_database functions

def save_texts_to_database(session, board_id, text_file_content):
    try:
        return _save_texts(session, board_id, text_file_content)
    except Exception as e:
        session.rollback()
        print(f"Error saving to database: {str(e)}")
        return False

def _save_texts(session, board_id, text_file_content):
    text_file_bytes = text_file_content.encode()

    # Save both texts to database
    create_info_txt(session, board_id, text_file_bytes)

    # Commit the transaction
    session.commit()
    return True

def generate_logical_net_text(source_db_path, board_id):
    conn = sqlite3.connect(source_db_path)
    cursor = conn.cursor()
    
    if board_id:
        cursor.execute("SELECT DISTINCT ln.name FROM logical_net ln WHERE ln.board_id = ?", (board_id,))
    else:
        cursor.execute("SELECT DISTINCT ln.name FROM logical_net ln")
    
    logical_nets = cursor.fetchall()
    logical_net_content = ""

    for net_name_tuple in logical_nets:
        net_name = net_name_tuple[0]
        query = """
        SELECT c.name AS component_name, p.name AS pin_name 
        FROM net_pin np
        JOIN logical_net ln ON np.logical_net_id = ln.id
        JOIN component c ON np.component_id = c.id
        JOIN pin p ON np.pin_id = p.id
        WHERE ln.name = ?
        """
        
        params = [net_name]
        if board_id:
            query += " AND ln.board_id = ?"
            params.append(board_id)
            
        cursor.execute(query, params)
        connections = cursor.fetchall()
        connection_strings = [f"{comp} at P{pin}" for comp, pin in connections]
        
        if not net_name.startswith("Unused"):
            logical_net_content += f"Logical net {net_name} connects {', '.join(connection_strings)}.\n"
    
    print(f"Logical net connections generated.")
    conn.close()
    
    # Create a new session for database operations
    session = Session()
    # Save to database
    save_texts_to_database(session, board_id, logical_net_content)

def generate_component_list(source_db_path, board_id):
    conn = sqlite3.connect(source_db_path)
    cursor = conn.cursor()
    
    query = "SELECT name, part FROM component"
    params = []
    if board_id:
        query += " WHERE board_id = ?"
        params.append(board_id)
    query += " ORDER BY name"
    
    cursor.execute(query, params)
    components = cursor.fetchall()
    
    component_list_content = ""
    
    for i, comp in enumerate(components, 1):
        component_name = comp[0]
        component_part = comp[1]
        component_list_content += f"{i}. {component_name} - {component_part}\n"
    
    print(f"Component list generated.")
    conn.close()
    
    # Create a new session for database operations
    session = Session()
    # Save to database
    save_texts_to_database(session, board_id, component_list_content)
