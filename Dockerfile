# Usa un'immagine base Python leggera
FROM python:3.10-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia gli eseguibili generati da PyInstaller
COPY dist/start_all /app/start_all
COPY dist/server_ipc /app/server_ipc
COPY dist/server_crop /app/server_crop
COPY dist/server_gen /app/server_gen
COPY dist/gateway /app/gateway

# Copia i file di database pre-popolati
COPY arboard.db /app/arboard.db
COPY crop.db /app/crop.db
COPY gen_server.db /app/gen_server.db

# Copia il file requirements.txt per installare eventuali dipendenze
COPY requirements.txt /app/requirements.txt

# Installa le dipendenze necessarie (se ce ne sono)
RUN pip install --no-cache-dir -r requirements.txt

# Espone le porte necessarie
EXPOSE 5000

# Comando di avvio
CMD ["./start_all"]
