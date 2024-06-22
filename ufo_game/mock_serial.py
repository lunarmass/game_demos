import time
import threading

class MockSerial:
    def __init__(self):
        self.in_waiting = 0
        self.lock = threading.Lock()
        self.data = []
        self.read_pos = 0

    def write(self, data):
        with self.lock:
            print(f"MockSerial write: {data.decode('utf-8')}")
            self.data.append(data.decode('utf-8').strip())
            self.in_waiting += len(data)

    def readline(self):
        with self.lock:
            if self.in_waiting > 0:
                response = self.generate_mock_response(self.data[self.read_pos])
                self.read_pos += 1
                self.in_waiting -= 1
                return response.encode('utf-8')
            return b''

    def generate_mock_response(self, command):
        responses = {
            "set_pulse": "ack:set_pulse",
            "set_detents": "ack:set_detents",
            "set_force": "ack:set_force",
            "set_mode": "ack:set_mode",
            "set_row": "ack:set_row",
        }
        return responses.get(command, "ack:unknown")

    def simulate_incoming_data(self):
        def simulate():
            while True:
                with self.lock:
                    self.data.append(f"accelerometer_x:{1.0}")
                    self.data.append(f"accelerometer_y:{2.0}")
                    self.data.append(f"accelerometer_z:{3.0}")
                    self.data.append(f"gyro_x:{0.1}")
                    self.data.append(f"gyro_y:{0.2}")
                    self.data.append(f"gyro_z:{0.3}")
                    self.data.append(f"force:{9.81}")
                    self.data.append(f"position:{5.0}")
                    self.data.append(f"velocity:{0.5}")
                    self.data.append(f"status:ok")
                    self.in_waiting += 10
                time.sleep(0.1)

        thread = threading.Thread(target=simulate)
        thread.daemon = True
        thread.start()
