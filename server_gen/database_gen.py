# Creo il file database_gen.py
from sqlalchemy import create_engine, Column, Text, Integer, String, Float, ForeignKey, CheckConstraint, LargeBinary, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import sqlite3

####
# Database setup
####

Base = declarative_base()
engine = create_engine('sqlite:///gen_server.db')
Session = sessionmaker(bind=engine)

####
# Models defined
####

class Group(Base):
    __tablename__ = 'group'
    group_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    
    components = relationship("Component", back_populates="group")

class Component(Base):
    __tablename__ = 'component'
    component_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    general_info = Column(Text, nullable=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    group_id = Column(Integer, ForeignKey('group.group_id'))
    
    group = relationship("Group", back_populates="components")

# Database init
def init_db():
    Base.metadata.create_all(engine)

####
# CRUD for Group
####

def get_all_groups(session):
    return session.query(Group).all()

def get_group(session, group_id):
    return session.query(Group).filter_by(group_id=group_id).first()

def create_group(session, name):
    group = Group(name=name)
    session.add(group)
    session.commit()
    return group

def update_group(session, group_id, name=None):
    group = session.query(Group).filter_by(group_id=group_id).first()
    if not group:
        return False
    
    if name is not None:
        group.name = name
    
    session.commit()
    return True

def delete_group(session, group_id):
    try:
        group = session.query(Group).filter_by(group_id=group_id).first()
        if not group:
            return False, "Group not found"
        
        # Check if there are components associated with this group
        components = session.query(Component).filter_by(group_id=group_id).count()
        if components > 0:
            return False, "Cannot delete group: there are components associated with it"
        
        session.delete(group)
        session.commit()
        return True, f"Group {group_id} deleted successfully"
    
    except Exception as e:
        session.rollback()
        return False, f"Error during delete: {str(e)}"

def deep_delete_group(session, group_id):
    try:
        group = session.query(Group).filter_by(group_id=group_id).first()
        if not group:
            return False, "Group not found"
        
        # Delete all components in this group
        session.query(Component).filter_by(group_id=group_id).delete()
        
        # Delete the group
        session.delete(group)
        session.commit()
        
        return True, f"Group {group_id} and all related components deleted successfully"
    
    except Exception as e:
        session.rollback()
        return False, f"Error during deep delete: {str(e)}"

####
# CRUD for Component
####

def get_all_components(session):
    return session.query(Component).all()

def get_component(session, component_id):
    return session.query(Component).filter_by(component_id=component_id).first()

def get_components_by_group(session, group_id):
    return session.query(Component).filter_by(group_id=group_id).all()

def create_component(session, name, type=None, general_info=None, x=None, y=None, group_id=None):
    component = Component(
        name=name,
        type=type,
        general_info=general_info,
        x=x,
        y=y,
        group_id=group_id
    )
    session.add(component)
    session.commit()
    return component

def update_component(session, component_id, name=None, type=None, general_info=None, x=None, y=None, group_id=None):
    component = session.query(Component).filter_by(component_id=component_id).first()
    if not component:
        return False
    
    if name is not None:
        component.name = name
    if type is not None:
        component.type = type
    if general_info is not None:
        component.general_info = general_info
    if x is not None:
        component.x = x
    if y is not None:
        component.y = y
    if group_id is not None:
        component.group_id = group_id
    
    session.commit()
    return True

def delete_component(session, component_id):
    try:
        component = session.query(Component).filter_by(component_id=component_id).first()
        if not component:
            return False, "Component not found"
        
        session.delete(component)
        session.commit()
        return True, f"Component {component_id} deleted successfully"
    
    except Exception as e:
        session.rollback()
        return False, f"Error during delete: {str(e)}"

####
# General operations
####

def clear_all_database(session):
    try:
        session.query(Component).delete()
        session.query(Group).delete()
        session.commit()
        return True
    
    except Exception as e:
        session.rollback()
        raise e