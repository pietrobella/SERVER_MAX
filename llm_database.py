import sqlite3
from server_ipc.database_ipc import create_info_txt, Session

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

# Example usage
if __name__ == "__main__":
    source_db_path = "arboard.db"    # Your source database
    board_id = 1  # Specify your board ID
    generate_logical_net_text(source_db_path, board_id)
    generate_component_list(source_db_path, board_id)
