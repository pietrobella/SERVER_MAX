import subprocess
import time
import signal
import os
import logging

os.environ['FLASK_ENV'] = 'production'
if os.environ.get('FLASK_ENV') != 'development':
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

import platform

development = True

IS_WINDOWS = platform.system() == "Windows"

if (development):
    VENV_PYTHON = os.path.join(os.getcwd(), '.venv', 'Scripts', 'python.exe')

    IPC_SERVER_COMMAND = [VENV_PYTHON, 'server_ipc/server_ipc.py']
    CROP_SERVER_COMMAND = [VENV_PYTHON, 'server_crop/server_crop.py']
    GEN_SERVER_COMMAND = [VENV_PYTHON, 'server_gen/server_gen.py']
    GATEWAY_COMMAND = [VENV_PYTHON, 'gateway.py']

else:
    PYTHON_EXEC = "python"

    IPC_SERVER_COMMAND = [PYTHON_EXEC, 'server_ipc/server_ipc.py']
    CROP_SERVER_COMMAND = [PYTHON_EXEC, 'server_crop/server_crop.py']
    GEN_SERVER_COMMAND = [PYTHON_EXEC, 'server_gen/server_gen.py']
    GATEWAY_COMMAND = [PYTHON_EXEC, 'gateway.py']

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
            print(f"Process {process.pid} terminated.")
        except Exception as e:
            print(f"Error during process termination: {e}")

if __name__ == '__main__':
    print("Starting servers...")

    # Start servers in order
    ipc_server_process = start_process(IPC_SERVER_COMMAND)
    print("IPC Server started on port 5001")

    crop_server_process = start_process(CROP_SERVER_COMMAND)
    print("Crop Server started on port 5002")

    gen_server_process = start_process(GEN_SERVER_COMMAND)
    print("Gen Server started on port 5003")

    # Wait a bit before starting the gateway
    time.sleep(2)

    gateway_process = start_process(GATEWAY_COMMAND)
    print("Gateway started on port 5000")

    print("\nAll servers have been started!")
    print("Gateway available on: http://localhost:5000")
    print("- IPC API: http://localhost:5000/ipc/...")
    print("- Crop API: http://localhost:5000/crop/...")
    print("- Gen API: http://localhost:5000/gen/...")
    print("\nHTTP request logs will appear below:")
    print("-" * 50)

    try:
        gateway_process.wait()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected.")
    finally:
        print("Stopping servers...")
        stop_process(gateway_process)
        stop_process(gen_server_process)
        stop_process(crop_server_process)
        stop_process(ipc_server_process)
        print("All servers have been stopped.")