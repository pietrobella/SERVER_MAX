import subprocess
import time
import signal
import os
import platform

IS_WINDOWS = platform.system() == "Windows"

VENV_PYTHON = os.path.join(os.getcwd(), '.venv', 'Scripts', 'python.exe')

IPC_SERVER_COMMAND = [VENV_PYTHON, 'server_ipc/server_ipc.py']
CROP_SERVER_COMMAND = [VENV_PYTHON, 'server_crop/server_crop.py']
GATEWAY_COMMAND = [VENV_PYTHON, 'gateway.py']

def start_process(command):
    process = subprocess.Popen(command)
    return process

def stop_process(process):
    if process:
        try:
            if IS_WINDOWS:
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            process.wait()
            print(f"Processo {process.pid} terminato.")
        except Exception as e:
            print(f"Errore durante l'arresto del processo: {e}")

if __name__ == '__main__':
    print("Avvio dei server...")
    ipc_server_process = start_process(IPC_SERVER_COMMAND)
    crop_server_process = start_process(CROP_SERVER_COMMAND)
    time.sleep(2)
    gateway_process = start_process(GATEWAY_COMMAND)

    try:
        gateway_process.wait()
    except KeyboardInterrupt:
        print("Interruzione da tastiera rilevata.")
    finally:
        print("Arresto dei server...")
        stop_process(ipc_server_process)
        stop_process(crop_server_process)
        print("Tutti i server sono stati arrestati.")