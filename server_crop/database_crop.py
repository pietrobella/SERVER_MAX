from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, CheckConstraint, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine('sqlite:///crop.db')
Session = sessionmaker(bind=engine)

# Models defined
class Board(Base):
    __tablename__ = 'board'
    ID_Board = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class Schematic(Base):
    __tablename__ = 'schematic'
    ID_Schematic = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    image = Column(LargeBinary, nullable=False)
    ID_Board = Column(Integer, ForeignKey('board.ID_Board'))

class Placement(Base):
    __tablename__ = 'placement'
    ID_Placement = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    side = Column(String, nullable=False)
    image = Column(LargeBinary, nullable=False)
    ID_Board = Column(Integer, ForeignKey('board.ID_Board'))
    __table_args__ = (CheckConstraint("side IN ('top', 'bottom')"),)

class Component(Base):
    __tablename__ = 'component'
    ID_Component = Column(Integer, primary_key=True)
    name_component = Column(String, nullable=False)
    more_info = Column(String(1000))
    ID_Board = Column(Integer, ForeignKey('board.ID_Board'))

class C_P(Base):
    __tablename__ = 'c_p'
    ID_Component = Column(Integer, ForeignKey('component.ID_Component'), primary_key=True)
    ID_Placement = Column(Integer, ForeignKey('placement.ID_Placement'))
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)

class C_S(Base):
    __tablename__ = 'c_s'
    ID_Component = Column(Integer, ForeignKey('component.ID_Component'), primary_key=True)
    ID_Schematic = Column(Integer, ForeignKey('schematic.ID_Schematic'), primary_key=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)

# Database init
def init_db():
    Base.metadata.create_all(engine)

# CREATE operations
def add_board(name):
    """Aggiunge una nuova board al database"""
    session = Session()
    board = Board(name=name)
    session.add(board)
    session.commit()
    board_id = board.ID_Board
    session.close()
    return board_id

def add_component(name, more_info=None, board_id=None):
    """Aggiunge un nuovo componente al database"""
    session = Session()
    component = Component(name_component=name, more_info=more_info, ID_Board=board_id)
    session.add(component)
    session.commit()
    component_id = component.ID_Component
    session.close()
    return component_id

def add_schematic(name, image, board_id=None):
    """Aggiunge un nuovo schematico al database"""
    session = Session()
    schematic = Schematic(name=name, image=image, ID_Board=board_id)
    session.add(schematic)
    session.commit()
    schematic_id = schematic.ID_Schematic
    session.close()
    return schematic_id

def add_placement(name, side, image, board_id=None):
    """Aggiunge un nuovo placement al database"""
    if side not in ['top', 'bottom']:
        raise ValueError("Side must be 'top' or 'bottom'")

    session = Session()
    placement = Placement(name=name, side=side, image=image, ID_Board=board_id)
    session.add(placement)
    session.commit()
    placement_id = placement.ID_Placement
    session.close()
    return placement_id

def add_component_placement(component_id, placement_id, x, y):
    """Associa un componente a un placement con coordinate x,y"""
    session = Session()

    # Verifica che il componente e il placement esistano
    component = session.query(Component).filter_by(ID_Component=component_id).first()
    placement = session.query(Placement).filter_by(ID_Placement=placement_id).first()

    if not component or not placement:
        session.close()
        raise ValueError("Componente or Placement not find")

    # Verifica se esiste già un'associazione per questo componente
    existing = session.query(C_P).filter_by(ID_Component=component_id).first()
    if existing:
        session.close()
        raise ValueError(f"Component {component_id} already associated with placement {existing.ID_Placement}")

    cp = C_P(ID_Component=component_id, ID_Placement=placement_id, x=x, y=y)
    session.add(cp)
    session.commit()
    session.close()
    return True

def add_component_schematic(component_id, schematic_id, x, y):
    """Associa un componente a uno schematico con coordinate x,y"""
    session = Session()

    # Verifica che il componente e lo schematico esistano
    component = session.query(Component).filter_by(ID_Component=component_id).first()
    schematic = session.query(Schematic).filter_by(ID_Schematic=schematic_id).first()

    if not component or not schematic:
        session.close()
        raise ValueError("Component or Schematic not found")

    # Verifica se esiste già un'associazione per questa coppia
    existing = session.query(C_S).filter_by(
        ID_Component=component_id,
        ID_Schematic=schematic_id
    ).first()

    if existing:
        session.close()
        raise ValueError(f"Component {component_id} already associated with placement{schematic_id}")

    cs = C_S(ID_Component=component_id, ID_Schematic=schematic_id, x=x, y=y)
    session.add(cs)
    session.commit()
    session.close()
    return True

# READ operations
def get_board(board_id):
    """Ottiene una board dal suo ID"""
    session = Session()
    board = session.query(Board).filter_by(ID_Board=board_id).first()
    result = None
    if board:
        result = {"id": board.ID_Board, "name": board.name}
    session.close()
    return result

def get_all_boards():
    """Ottiene tutte le boards"""
    session = Session()
    boards = session.query(Board).all()
    result = [{"id": b.ID_Board, "name": b.name} for b in boards]
    session.close()
    return result

def get_component(component_id):
    """Ottiene un componente dal suo ID"""
    session = Session()
    component = session.query(Component).filter_by(ID_Component=component_id).first()
    result = None
    if component:
        result = {
            "id": component.ID_Component,
            "name": component.name_component,
            "more_info": component.more_info,
            "board_id": component.ID_Board
        }
    session.close()
    return result

def get_all_components():
    """Ottiene tutti i componenti"""
    session = Session()
    components = session.query(Component).all()
    result = [
        {
            "id": c.ID_Component,
            "name": c.name_component,
            "more_info": c.more_info,
            "board_id": c.ID_Board
        } for c in components
    ]
    session.close()
    return result

def get_schematic(schematic_id):
    """Ottiene uno schematico dal suo ID"""
    session = Session()
    schematic = session.query(Schematic).filter_by(ID_Schematic=schematic_id).first()
    result = None
    if schematic:
        result = {"id": schematic.ID_Schematic, "name": schematic.name, "board_id": schematic.ID_Board}
    session.close()
    return result

def get_all_schematics():
    """Ottiene tutti gli schematici"""
    session = Session()
    schematics = session.query(Schematic).all()
    result = [{"id": s.ID_Schematic, "name": s.name, "board_id": s.ID_Board} for s in schematics]
    session.close()
    return result

def get_schematic_image(schematic_id):
    """Ottiene l'immagine di uno schematico dal suo ID"""
    session = Session()
    schematic = session.query(Schematic).filter_by(ID_Schematic=schematic_id).first()
    result = None
    if schematic:
        result = schematic.image
    session.close()
    return result

def get_placement(placement_id):
    """Ottiene un placement dal suo ID"""
    session = Session()
    placement = session.query(Placement).filter_by(ID_Placement=placement_id).first()
    result = None
    if placement:
        result = {"id": placement.ID_Placement, "name": placement.name, "side": placement.side, "board_id": placement.ID_Board}
    session.close()
    return result

def get_all_placements():
    """Ottiene tutti i placements"""
    session = Session()
    placements = session.query(Placement).all()
    result = [{"id": p.ID_Placement, "name": p.name, "side": p.side, "board_id": p.ID_Board} for p in placements]
    session.close()
    return result

def get_placement_image(placement_id):
    """Ottiene l'immagine di un placement dal suo ID"""
    session = Session()
    placement = session.query(Placement).filter_by(ID_Placement=placement_id).first()
    result = None
    if placement:
        result = placement.image
    session.close()
    return result

def get_component_placements(component_id):
    """Ottiene il placement associato a un componente"""
    session = Session()
    cp = session.query(C_P).filter_by(ID_Component=component_id).first()
    result = None
    if cp:
        placement = session.query(Placement).filter_by(ID_Placement=cp.ID_Placement).first()
        result = {
            "component_id": cp.ID_Component,
            "placement_id": cp.ID_Placement,
            "placement_name": placement.name if placement else None,
            "placement_side": placement.side if placement else None,
            "x": cp.x,
            "y": cp.y
        }
    session.close()
    return result

def get_component_schematics(component_id):
    """Ottiene tutti gli schematici associati a un componente"""
    session = Session()
    cs_list = session.query(C_S).filter_by(ID_Component=component_id).all()
    result = []
    for cs in cs_list:
        schematic = session.query(Schematic).filter_by(ID_Schematic=cs.ID_Schematic).first()
        result.append({
            "component_id": cs.ID_Component,
            "schematic_id": cs.ID_Schematic,
            "schematic_name": schematic.name if schematic else None,
            "x": cs.x,
            "y": cs.y
        })
    session.close()
    return result

# UPDATE operations
def update_board(board_id, name):
    """Aggiorna una board esistente"""
    session = Session()
    board = session.query(Board).filter_by(ID_Board=board_id).first()
    if not board:
        session.close()
        return False

    board.name = name
    session.commit()
    session.close()
    return True

def update_component(component_id, name, more_info=None, board_id=None):
    """Aggiorna un componente esistente"""
    session = Session()
    component = session.query(Component).filter_by(ID_Component=component_id).first()
    if not component:
        session.close()
        return False

    component.name_component = name
    if more_info is not None:
        component.more_info = more_info
    if board_id is not None:
        component.ID_Board = board_id
    session.commit()
    session.close()
    return True

def update_schematic(schematic_id, name, image, board_id=None):
    """Aggiorna uno schematico esistente"""
    session = Session()
    schematic = session.query(Schematic).filter_by(ID_Schematic=schematic_id).first()
    if not schematic:
        session.close()
        return False

    schematic.name = name
    schematic.image = image
    if board_id is not None:
        schematic.ID_Board = board_id
    session.commit()
    session.close()
    return True

def update_placement(placement_id, name, side, image, board_id=None):
    """Aggiorna un placement esistente"""
    if side not in ['top', 'bottom']:
        raise ValueError("Side must be 'top' or 'bottom'")

    session = Session()
    placement = session.query(Placement).filter_by(ID_Placement=placement_id).first()
    if not placement:
        session.close()
        return False

    placement.name = name
    placement.side = side
    placement.image = image
    if board_id is not None:
        placement.ID_Board = board_id
    session.commit()
    session.close()
    return True

def update_component_placement(component_id, placement_id, x, y):
    """Aggiorna l'associazione tra componente e placement"""
    session = Session()
    cp = session.query(C_P).filter_by(ID_Component=component_id).first()
    if not cp:
        session.close()
        return False

    cp.ID_Placement = placement_id
    cp.x = x
    cp.y = y
    session.commit()
    session.close()
    return True

def update_component_schematic(component_id, schematic_id, x, y):
    """Aggiorna l'associazione tra componente e schematico"""
    session = Session()
    cs = session.query(C_S).filter_by(
        ID_Component=component_id,
        ID_Schematic=schematic_id
    ).first()

    if not cs:
        session.close()
        return False

    cs.x = x
    cs.y = y
    session.commit()
    session.close()
    return True

# DELETE operations
def delete_board(board_id):
    """Elimina una board"""
    session = Session()
    result = session.query(Board).filter_by(ID_Board=board_id).delete()
    session.commit()
    session.close()
    return result > 0

def delete_component(component_id):
    """Elimina un componente e tutte le sue associazioni"""
    session = Session()

    # Elimina prima le associazioni
    session.query(C_P).filter_by(ID_Component=component_id).delete()
    session.query(C_S).filter_by(ID_Component=component_id).delete()

    # Poi elimina il componente
    result = session.query(Component).filter_by(ID_Component=component_id).delete()
    session.commit()
    session.close()
    return result > 0

def delete_schematic(schematic_id):
    """Elimina uno schematico e tutte le sue associazioni"""
    session = Session()

    # Elimina prima le associazioni
    session.query(C_S).filter_by(ID_Schematic=schematic_id).delete()

    # Poi elimina lo schematico
    result = session.query(Schematic).filter_by(ID_Schematic=schematic_id).delete()
    session.commit()
    session.close()
    return result > 0

def delete_placement(placement_id):
    """Elimina un placement e tutte le sue associazioni"""
    session = Session()

    # Elimina prima le associazioni
    session.query(C_P).filter_by(ID_Placement=placement_id).delete()

    # Poi elimina il placement
    result = session.query(Placement).filter_by(ID_Placement=placement_id).delete()
    session.commit()
    session.close()
    return result > 0

def delete_component_placement(component_id):
    """Elimina l'associazione tra componente e placement"""
    session = Session()
    result = session.query(C_P).filter_by(ID_Component=component_id).delete()
    session.commit()
    session.close()
    return result > 0

def delete_component_schematic(component_id, schematic_id):
    """Elimina l'associazione tra componente e schematico"""
    session = Session()
    result = session.query(C_S).filter_by(
        ID_Component=component_id,
        ID_Schematic=schematic_id
    ).delete()
    session.commit()
    session.close()
    return result > 0

def clear_all_database():
    """Elimina tutti i dati dal database"""
    session = Session()

    # Elimina prima le associazioni (tabelle di join)
    result_cp = session.query(C_P).delete()
    result_cs = session.query(C_S).delete()

    # Poi elimina le entità principali
    result_comp = session.query(Component).delete()
    result_place = session.query(Placement).delete()
    result_schem = session.query(Schematic).delete()
    result_board = session.query(Board).delete()

    session.commit()
    session.close()

    total_deleted = result_cp + result_cs + result_comp + result_place + result_schem + result_board
    return total_deleted > 0