# Usa un'immagine base adatta al tuo ambiente (es. Python, Node.js, ecc.)
FROM python:3.12

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia i file delle dipendenze (es. requirements.txt)
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice sorgente dell'applicazione
COPY . /app

# Definisci la porta su cui l'applicazione ascolta (se necessario)
EXPOSE 8000

# Definisci il comando per avviare l'applicazione
CMD ["python", "start_all.py"]