import sqlite3
import os

def generate_logical_net_text(source_db_path, output_file, board_name=None):
    """
    Generate a text file with logical net connection descriptions
    directly from the source database without an intermediate table,
    filtered by board name if provided
    """
    conn = sqlite3.connect(source_db_path)
    cursor = conn.cursor()
    
    # If board_name is provided, get the board_id first
    board_id = None
    if board_name:
        cursor.execute("SELECT id FROM board WHERE name = ?", (board_name,))
        result = cursor.fetchone()
        if not result:
            print(f"Board '{board_name}' not found!")
            conn.close()
            return False
        board_id = result[0]
        
        # Get all distinct logical nets for this board
        cursor.execute("SELECT DISTINCT ln.name FROM logical_net ln WHERE ln.board_id = ?", (board_id,))
    else:
        # Get all distinct logical nets
        cursor.execute("SELECT DISTINCT ln.name FROM logical_net ln")
    
    logical_nets = cursor.fetchall()
    
    with open(output_file, 'w') as f:
        if board_name:
            f.write(f"Logical net connections for board: {board_name}\n")
            
        for net_name_tuple in logical_nets:
            net_name = net_name_tuple[0]
            
            # Get all connections for this logical net directly
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
                # Write the sentence
                f.write(f"Logical net {net_name} connects {', '.join(connection_strings)}.\n")
        
    print(f"Logical net connections written to {output_file}")
    conn.close()
    return True

def generate_component_list(source_db_path, output_file, board_name=None):
    """
    Generate a text file containing a list of all component names in the database,
    filtered by board name if provided
    """
    conn = sqlite3.connect(source_db_path)
    cursor = conn.cursor()
    
    # If board_name is provided, get the board_id first
    board_id = None
    if board_name:
        cursor.execute("SELECT id FROM board WHERE name = ?", (board_name,))
        result = cursor.fetchone()
        if not result:
            print(f"Board '{board_name}' not found!")
            conn.close()
            return False
        board_id = result[0]
    
    # Get all component names, filtered by board_id if provided
    query = "SELECT name, part FROM component"
    params = []
    if board_id:
        query += " WHERE board_id = ?"
        params.append(board_id)
    query += " ORDER BY name"
    
    cursor.execute(query, params)
    components = cursor.fetchall()
    
    with open(output_file, 'w') as f:
        if board_name:
            f.write(f"List of components for board: {board_name}\n")
        else:
            f.write("List of components in the database:\n")
        
        for i, comp in enumerate(components, 1):
            component_name = comp[0]
            component_part = comp[1]
            f.write(f"{i}. {component_name} - {component_part}\n")
    
    print(f"Component list written to {output_file}")
    conn.close()
    return True

def list_available_boards(source_db_path):
    """
    List all available boards in the database
    """
    conn = sqlite3.connect(source_db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM board ORDER BY name")
    boards = cursor.fetchall()
    
    print("\nAvailable boards:")
    for board_id, name in boards:
        print(f"ID: {board_id}, Name: {name}")
    
    conn.close()
    return boards

# Example usage
if __name__ == "__main__":
    source_db_path = "arboard.db"    # Your source database
    net_output_file = "logical_net_connections.txt"
    component_output_file = "component_list.txt"
    
    # List available boards
    available_boards = list_available_boards(source_db_path)
    
    # Choose a specific board or leave as None for all boards
    selected_board = "MB1136"  # Change this to the board name you want, or None for all boards
    
    generate_logical_net_text(source_db_path, net_output_file, selected_board)
    generate_component_list(source_db_path, component_output_file, selected_board)
