import serial
import serial.tools.list_ports
import threading
import time
import queue
from fastapi import FastAPI, HTTPException
import logging
import json
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.CRITICAL)

logger = logging.getLogger(__name__)

# Toggle this parameter to enable/disable offline testing
TEST_OFFLINE = False

if TEST_OFFLINE:
    from mock_serial import MockSerial as Serial
else:
    from serial import Serial

app = FastAPI()

# Function to find the ESP32 port dynamically
def find_esp32_port(device_name="USB Serial Device"):
    ports = list(serial.tools.list_ports.comports())
    logger.info(f"Available ports: {ports}")
    for port in ports:
        logger.info(f"Checking port: {port.description}, {port.name}, {port.hwid}")
        if device_name in port.description:
            return port.device
    return None

def initialize_serial_connection():
    global ser, port
    port = find_esp32_port("USB Serial Device")
    if port:
        logger.info(f"ESP32 device found at port: {port}")
        ser = Serial(port, 115200, timeout=1)
        return True
    return False

# Attempt to find the ESP32 port if not in offline mode
if not TEST_OFFLINE:
    logger.info("Searching for ESP32 device...")
    if not initialize_serial_connection():
        raise Exception("ESP32 device not found")
else:
    logger.info("Using mock serial for offline testing")
    ser = Serial()

# Lock for thread-safe serial communication
serial_lock = threading.Lock()

# Queue for incoming data
data_queue = queue.Queue()

# Shared state to manage incoming data
shared_state = {
    "accelerometer_x": None,
    "accelerometer_y": None,
    "accelerometer_z": None,
    "gyro_x": None,
    "gyro_y": None,
    "gyro_z": None,
    "force": None,
    "position": None,
    "velocity": None,
    "virtual_velocity": None,
    "status": None,
}

# Lock for thread-safe access to shared_state
state_lock = threading.Lock()

# Event to stop threads gracefully
stop_event = threading.Event()

# Function to continuously read from the serial port
def read_from_serial():
    logger.info("Started serial reading thread")
    while not stop_event.is_set():
        with serial_lock:
            try:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8').strip()
                    if line.startswith("DATA:"):
                        data_queue.put(line[5:])  # Strip the "DATA:" prefix
                    logger.debug(f"Received data: {line}")
                # print(f"Received data: {line}")
            except serial.SerialException as e:
                logger.error(f"Serial exception: {e}")
                ser.close()
                ser.port = None  # Ensure the serial object is reset
                logger.info("Attempting to reconnect to ESP32 device...")
                while not stop_event.is_set():
                    if initialize_serial_connection():
                        logger.info("Reconnected to ESP32 device")
                        break
                    time.sleep(1)
        time.sleep(0.01)

def process_incoming_data():
    logger.info("Started data processing thread")
    while not stop_event.is_set():
        data_processed = False
        while not data_queue.empty():
            data = data_queue.get()  # Get data from the queue
            try:
                # Split the data packet based on the custom separator
                values = data.split("|")
                with state_lock:
                    for value in values:
                        key, val = value.split(":")
                        if key in shared_state:
                            shared_state[key] = float(val) if val.replace('.', '', 1).isdigit() else val
                            data_processed = True
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to process data: {data}, error: {e}")
                pass
        if data_processed:
            with state_lock:
                logger.info(f"Current data packet: {shared_state}")
                # print(f"Current data packet: {shared_state}")
        time.sleep(0.02)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting serial reading thread...")
    read_thread = threading.Thread(target=read_from_serial)
    read_thread.daemon = True
    read_thread.start()

    logger.info("Starting data processing thread...")
    process_thread = threading.Thread(target=process_incoming_data)
    process_thread.daemon = True
    process_thread.start()

    yield

    logger.info("Shutting down threads...")
    stop_event.set()
    read_thread.join()
    process_thread.join()
    logger.info("Threads successfully shut down")

app = FastAPI(lifespan=lifespan)

@app.get("/status")
def get_status():
    if TEST_OFFLINE:
        return {"status": "running in offline mode"}
    else:
        return {"status": "running"}

@app.get("/data")
def get_data():
    # print(f"Request received at: {time.time()}")
    with state_lock:
        return shared_state.copy()

@app.post("/send_command")
def send_command(command: dict):
    with serial_lock:
        print(f"Sending command: {command}")
        command_str = json.dumps(command)
        ser.write(command_str.encode('utf-8'))
        ser.write(b'\n')
    return {"status": "command sent"}

@app.get("/ack")
def get_ack():
    with serial_lock:
        if ser.in_waiting:
            ack = ser.readline().decode('utf-8').strip()
            return {"ack": ack}
        else:
            raise HTTPException(status_code=404, detail="No ACK received")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
