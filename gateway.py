from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from voice_assistant_for_server import process_wav_file 

app = Flask(__name__)
CORS(app)  # Abilita CORS per tutte le route

# Configurazione dei server interni
IPC_SERVER_URL = 'http://localhost:5001'
CROP_SERVER_URL = 'http://localhost:5002'

# Funzione di routing generica
def route_request(server_url, path):
    url = f'{server_url}{path}'
    try:
        # Gestione speciale per upload di file
        if request.files:
            # Per richieste multipart/form-data (upload file)
            files = {name: (file.filename, file.stream, file.content_type)
                    for name, file in request.files.items()}

            # Includi anche i dati del form se presenti
            form_data = request.form.to_dict() if request.form else None

            response = requests.request(
                method=request.method,
                url=url,
                files=files,
                data=form_data,
                params=request.args,
                stream=True
            )
        else:
            # Per richieste normali (JSON, ecc.)
            headers = {key: value for key, value in request.headers.items()
                      if key.lower() not in ['host', 'content-length']}

            response = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.get_data(),
                params=request.args,
                stream=True
            )

        # Prepara la risposta mantenendo status code e headers
        return response.content, response.status_code, dict(response.headers)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Gateway error: {str(e)}'}), 500, {}

# Route per IPC
@app.route('/ipc/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def ipc_route(path):
    content, status_code, headers = route_request(IPC_SERVER_URL, f'/api/{path}')
    return content, status_code, headers

# Route per Crop
@app.route('/crop/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def crop_route(path):
    content, status_code, headers = route_request(CROP_SERVER_URL, f'/api/{path}')
    return content, status_code, headers

# Pagina principale del gateway
@app.route('/')
def index():
    return jsonify({
        "message": "API Gateway",
        "endpoints": {
            "IPC API": "/ipc/...",
            "Crop API": "/crop/..."
        }
    })

# Gestione errori 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

# Gestione errori 500
@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# Funzione di assistenza vocale (placeholder)

@app.route('/voice-assistance', methods=['POST'])
def voice_assistance_route():
    if 'file' not in request.files:
        return jsonify({"error": "Nessun file inviato"}), 400
    wav_file = request.files['file']
    if not wav_file.filename.lower().endswith('.wav'):
        return jsonify({"error": "Il file deve essere un WAV"}), 400
    # Chiamata alla funzione di assistenza vocale
    result = process_wav_file(wav_file)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)