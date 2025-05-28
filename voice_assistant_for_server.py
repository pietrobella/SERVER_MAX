from flask import Flask, request, jsonify
import os
import json
import speech_recognition as sr
import google.generativeai as genai
from PyPDF2 import PdfReader

app = Flask(__name__)

llm_api_key = "AIzaSyCk6uHZC42lQlENdmPIyP6n8MV66RFh3Qo"
llm_model = "gemini-1.5-flash"
genai.configure(api_key=llm_api_key)

import sqlite3
from PyPDF2 import PdfReader
import io

def load_pdf_content_from_db(board_id):
    """
    Load PDF content from the database for a specific board ID.
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect("arboard.db")
        cursor = conn.cursor()

        # Query to fetch the PDF file for the given board_id
        cursor.execute("SELECT file_pdf FROM user_manual WHERE board_id = ?", (board_id,))
        result = cursor.fetchone()

        if not result:
            print(f"No PDF found for board_id: {board_id}")
            return ""

        # The PDF file is stored as a BLOB in the database
        pdf_blob = result[0]

        # Convert the BLOB to a file-like object
        pdf_file = io.BytesIO(pdf_blob)

        # Use PyPDF2 to read the PDF content
        reader = PdfReader(pdf_file)
        content = []

        total_pages = len(reader.pages)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                content.append(f"Page {i+1}: {text}")

        pdf_content = "\n\n".join(content)

        # Close the database connection
        conn.close()

        return pdf_content

    except Exception as e:
        print(f"Error loading PDF content from database: {e}")
        return ""

def load_text_files_content_from_db(board_id):
    """
    Load PDF content from the database for a specific board ID.
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect("arboard.db")
        cursor = conn.cursor()

        # Query to fetch the PDF file for the given board_id
        cursor.execute("SELECT file_txt FROM info_txt WHERE board_id = ?", (board_id,))
        result = cursor.fetchone()

        if not result:
            print(f"No PDF found for board_id: {board_id}")
            return ""

        # The PDF file is stored as a BLOB in the database
        pdf_blob = result[0]

        # Convert the BLOB to a file-like object
        pdf_file = io.BytesIO(pdf_blob)

        # Use PyPDF2 to read the PDF content
        reader = PdfReader(pdf_file)
        content = []

        total_pages = len(reader.pages)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                content.append(f"Page {i+1}: {text}")

        pdf_content = "\n\n".join(content)

        # Close the database connection
        conn.close()

        return pdf_content

    except Exception as e:
        print(f"Error loading PDF content from database: {e}")
        return ""

def load_text_files():    
    try:
        '''
        # Load PDF content
        # pdf_path = os.path.join("Loading", "llm_source_files", "board_manual.pdf")
        pdf_path = os.path.join("info_llm", "um1974-stm32-nucleo144-boards-mb1137-stmicroelectronics.pdf")
        reader = PdfReader(pdf_path)
        content = []
        
        total_pages = len(reader.pages)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                content.append(f"Page {i+1}: {text}")
        
        pdf_content = "\n\n".join(content)

        '''
        # Load all text files from the specified directory
        other_files_content = ""
        other_files_path = "info_llm"
        
        try:
            # List all .txt files in the directory
            for filename in os.listdir(other_files_path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(other_files_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        other_files_content += f.read() + "\n\n"  # Append content with separation
        except Exception as e:
            print(f"Error reading text files: {e}")
        
        return other_files_content
    
    except Exception as e:
        print(f"Error loading PDF content: {e}")
        return ""

# Function to process the WAV file and extract text
def process_wav_file(wav_file):
    """
    Process the WAV file and extract text.
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            print(f"Processing WAV audio from: {wav_file}")
            audio = recognizer.record(source)
        
        # Recognize the speech
        extracted_text = recognizer.recognize_google(audio)
        print(f"Recognized from WAV: {extracted_text}")
        
        response = process_query(extracted_text)
        
        # Ensure response is a dictionary
        if isinstance(response, dict):
            return response
        else:
            return {"error": "Unexpected response format from process_query."}
    
    except Exception as e:
        return {"error": str(e)}  # Return error as a JSON serializable dict


# Function to process the query and generate a response
def process_query(query):
    """
    Process the query and generate a response.
    """
    # Set up the Gemini model
    model = genai.GenerativeModel(llm_model)
    pdf_content = load_pdf_content_from_db(1)
    other_files_content = load_text_files_content_from_db(1)
    
    prompt = f"""
    You are a specialized electronic engineering assistant that helps users with questions about microcontroller-based boards.
    
    You have access to the following resources:
    * board_manual.pdf: Complete documentation for the microcontroller board
    * logical_net_connections.txt: Structured list of notable components and their functions
    
    When responding to questions:
    1. Search both documents for information relevant to the query
    2. Provide a clear, technically accurate explanation that answers the user's question
    3. Reference specific components, pins, configurations or code examples as needed
    4. Balance technical accuracy with accessibility, using proper terminology
    
    Please answer the question based ONLY on the information provided in these documents.
    Write your answer in a sentence format, in a user-friendly manner.
    Include the source of the information in your answer, such as "According to the manual" or "As per the components list" at the end of your response.
    If the answer is not found in the provided information, please say "I don't have enough information to answer this question."
    
    MANUAL CONTENT:
    {pdf_content[:3000]}
    
    COMPONENTS INFORMATION FILES CONTENT:
    {other_files_content[:3000]}
    
    QUESTION: {query}
    """
    
    # Generate response
    genai_response = model.generate_content(prompt)
    response = genai_response.text
    print(f"Generated response: {response}")
    json_response = extract_structured_response(query, response)
    print(f"Generated json response: {json_response}")
    return json_response

# Function to extract structured data from the query and response
def extract_structured_response(query, response):
    """
    Extract structured data from the query and response.
    """
    # Set up the Gemini model for structured extraction
    model = genai.GenerativeModel(llm_model)
    pdf_content = load_pdf_content_from_db(1)
    other_files_content = load_text_files_content_from_db(1)
    
    # Create a structured extraction prompt
    prompt = f"""
    You are a specialized component extraction agent for microcontroller boards.
    
    Your task is to process:
    
    1. The original user question about a microcontroller board
    2. The comprehensive answer provided by the first analysis agent
    
    You have access to the same reference materials:
    
    # PDF manual content is available as a string variable
    
    MANUAL CONTENT = '''
    {pdf_content[:3000]}
    '''
    
    # Components list content is available as a string variable
    
    COMPONENTS INFORMATION FILES CONTENT = '''
    {other_files_content[:3000]}
    '''
    
    Based on these inputs, generate a simplified JSON output that contains ONLY an array of
    component names that are most relevant to addressing the user's question.
    The component names should be extracted from the query, the response, and the PDF content,
    and they could be resistance labels, pin names, or any other relevant identifiers.
    For each component, only include the name, not any additional information or context.
    If in the query, it is asked for one name/element, return only one name as component.
    Return the component labels not the pin names, so if P1 connects R1 to something, return R1.
    
    Your output should follow this format:
    
    {{
    "query": "the user's original question",
    "response": "the full response that was provided",
    "components": ["component1", "component2", "component3"]
    }}
    
    QUERY: {query}
    
    RESPONSE: {response}
    """
    
    # Configure to return JSON
    generation_config = {
        "temperature": 0.2,
        "response_mime_type": "application/json"
    }
    
    # Generate structured response
    genai_response = model.generate_content(
        prompt,
        generation_config=generation_config
    )
    
    # Parse the resulting JSON
    components_data = json.loads(genai_response.text)
    
    # Create the full structured response
    structured_data = {
        "query": query,
        "response": response,
        "components": components_data.get("components", [])
    }
    print(f"Structured data extracted: {structured_data}")
    return structured_data