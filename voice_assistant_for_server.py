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
        # Use context manager for proper connection handling
        with sqlite3.connect("arboard.db") as conn:
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

            try:
                # Use PyPDF2 to read the PDF content
                reader = PdfReader(pdf_file)
                content = []

                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            content.append(f"Page {i+1}: {text}")
                    except Exception as page_error:
                        print(f"Error extracting text from page {i+1}: {page_error}")
                        continue

                pdf_content = "\n\n".join(content)
                return pdf_content
                
            except Exception as pdf_error:
                print(f"Error processing PDF: {pdf_error}")
                return ""

    except sqlite3.Error as e:
        print(f"Database error loading PDF: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error loading PDF: {e}")
        return ""


def load_text_files_content_from_db(board_id):
    """
    Load text content from the database for a specific board ID.
    """
    try:
        # Use context manager for proper connection handling
        with sqlite3.connect("arboard.db") as conn:
            cursor = conn.cursor()

            # Query to fetch the text file for the given board_id
            cursor.execute("SELECT file_txt FROM info_txt WHERE board_id = ?", (board_id,))
            results = cursor.fetchall()

            if not results:
                print(f"No text files found for board_id: {board_id}")
                return ""

            # Process all text files for this board
            text_content = []
            for result in results:
                # Text files should be decoded directly, not processed as PDF
                try:
                    # The text file is stored as a BLOB in the database
                    text_blob = result[0]
                    # Decode the binary data to string
                    text_str = text_blob.decode('utf-8')
                    text_content.append(text_str)
                except UnicodeDecodeError as e:
                    print(f"Error decoding text file: {e}")
                    continue

            return "\n\n".join(text_content)

    except sqlite3.Error as e:
        print(f"Database error loading text content: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error loading text content: {e}")
        return ""



# Function to process the WAV file and extract text
def process_wav_file(wav_file, board_id=1):
    """
    Process the WAV file and extract text.
    
    Args:
        wav_file (str): Path to the WAV file
        board_id (int, optional): The board ID to query. Defaults to 1.
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            print(f"Processing WAV audio from: {wav_file}")
            audio = recognizer.record(source)
        
        # Recognize the speech
        extracted_text = recognizer.recognize_google(audio)
        print(f"Recognized from WAV: {extracted_text}")
        
        response = process_query(extracted_text, board_id)
        
        # Ensure response is a dictionary
        if isinstance(response, dict):
            return response
        else:
            return {"error": "Unexpected response format from process_query.", "query": extracted_text, "components": []}
    
    except sr.UnknownValueError:
        return {"error": "Speech could not be recognized", "query": "", "components": []}
    except sr.RequestError as e:
        return {"error": f"Speech recognition service error: {e}", "query": "", "components": []}
    except Exception as e:
        return {"error": str(e), "query": "", "components": []}


def process_query(query, board_id=1):
    """
    Process the query and generate a response.
    
    Args:
        query (str): The user's question
        board_id (int, optional): The board ID to query. Defaults to 1.
    """
    # Set up the Gemini model
    model = genai.GenerativeModel(llm_model)
    
    # Load content from database with specified board_id
    pdf_content = load_pdf_content_from_db(board_id)
    other_files_content = load_text_files_content_from_db(board_id)
    
    prompt = f"""
    You are a specialized electronic engineering assistant that helps users with questions about microcontroller-based boards.

    You have access to the following resources:
    * board_manual.pdf: Complete documentation for the microcontroller board
    * logical_net_connections.txt: Structured list of notable components and their functions

    When responding to questions:
    1. Search both documents for information relevant to the query.
    2. Provide a clear, technically accurate explanation that answers the user's question.
    3. Reference specific components, pins, configurations or code examples as needed.
    4. Balance technical accuracy with accessibility, using proper terminology.
    5. **If the user asks for the location of a component (e.g., "where is component R7?"), respond with: "I am now illuminating component [component name] on the board."  Replace "[component name]" with the actual component name from the user's query.  Do not consult the documents for location information in this case.**

    Please answer other questions based ONLY on the information provided in these documents.
    Write your answer in a sentence format, in a user-friendly manner.
    Include the source of the information in your answer, such as "According to the manual" or "As per the components list" at the end of your response.
    If the answer is not found in the provided information, please say "I don't have enough information to answer this question."
        
    MANUAL CONTENT:
    {pdf_content[:3000] if pdf_content else "No manual content available."}
    
    COMPONENTS INFORMATION FILES CONTENT:
    {other_files_content[:3000] if other_files_content else "No components information available."}
    
    QUESTION: {query}
    """
    
    # Generate response
    try:
        genai_response = model.generate_content(prompt)
        response = genai_response.text
        print(f"Generated response: {response}")
        json_response = extract_structured_response(query, response, board_id)
        print(f"Generated json response: {json_response}")
        return json_response
    except Exception as e:
        print(f"Error generating response: {e}")
        return {"error": str(e), "query": query, "components": []}

# Function to extract structured data from the query and response
def extract_structured_response(query, response, board_id=1):
    """
    Extract structured data from the query and response.
    
    Args:
        query (str): The user's question
        response (str): The LLM's response
        board_id (int, optional): The board ID to query. Defaults to 1.
    """
    # Set up the Gemini model for structured extraction
    model = genai.GenerativeModel(llm_model)
    
    # Load content from database with specified board_id
    pdf_content = load_pdf_content_from_db(board_id)
    other_files_content = load_text_files_content_from_db(board_id)
    
    # Create a structured extraction prompt
    prompt = f"""
    You are a specialized component extraction agent for microcontroller boards.
    
    Your task is to process:
    
    1. The original user question about a microcontroller board
    2. The comprehensive answer provided by the first analysis agent
    
    You have access to the same reference materials:
    
    # PDF manual content is available as a string variable
    
    MANUAL CONTENT = '''
    {pdf_content[:3000] if pdf_content else "No manual content available."}
    '''
    
    # Components list content is available as a string variable
    
    COMPONENTS INFORMATION FILES CONTENT = '''
    {other_files_content[:3000] if other_files_content else "No components information available."}
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
    
    try:
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
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {"query": query, "response": response, "components": [], "error": "Failed to parse components"}
    except Exception as e:
        print(f"Error extracting structured response: {e}")
        return {"query": query, "response": response, "components": [], "error": str(e)}

'''
if __name__ == "__main__":
    pdf = load_text_files_content_from_db(1)
    print(f"Loaded text content: {pdf[:1000]}...")  # Print first 1000 characters for brevity
    text = load_pdf_content_from_db(1)
    print(f"Loaded PDF content: {text[:1000]}...")  # Print first 1000 characters for brevity
'''