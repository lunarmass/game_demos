import requests
import math
import asyncio
import threading

class DigitalWeightController:
    def __init__(self, api_url):
        self.api_url = api_url
        self.status = "starting"
        self.task_queue = asyncio.Queue()
        self.data_queue = asyncio.Queue()  # Queue to store controller data
        self.loop = asyncio.new_event_loop()
        self.stop_event = threading.Event()
        self.busy = False  # Busy flag
        self.thread = threading.Thread(target=self.start_loop, daemon=True)
        self.thread.start()

        # Calibration values
        self.flat_calibration = None
        self.up_calibration = None
        self.down_calibration = None
        self.left_calibration = None
        self.right_calibration = None
        self.offset_gyro_x = 540
        self.offset_gyro_y = -575
        self.offset_gyro_z = -420

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.process_tasks())
        except asyncio.CancelledError:
            pass

    async def process_tasks(self):
        while not self.stop_event.is_set() or not self.task_queue.empty():
            try:
                task = await self.task_queue.get()
                await task
                self.task_queue.task_done()
            except asyncio.CancelledError:
                break

    def enqueue_task(self, coro):
        task = self.loop.create_task(coro)
        self.loop.call_soon_threadsafe(self.task_queue.put_nowait, task)

    def get_status(self):
        response = self.loop.run_until_complete(self.get_controller_status())
        self.status = response.get("status", "starting")
        return self.status

    async def get_controller_status(self):
        response = await self.loop.run_in_executor(None, requests.get, f"{self.api_url}/status")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get status: {response.status_code}")

    async def get_controller_data(self):
        self.busy = True  # Set busy flag
        response = await self.loop.run_in_executor(None, requests.get, f"{self.api_url}/data")
        if response.status_code == 200:
            data = response.json()
            processed_data = self.process_controller_data(data)
            await self.data_queue.put(processed_data)  # Put processed data into the queue
        else:
            raise Exception(f"Failed to get data: {response.status_code}")
        self.busy = False  # Clear busy flag

    def process_controller_data(self, data):
        x = float(data.get("accelerometer_x", 0) or 0)
        y = float(data.get("accelerometer_y", 0) or 0)
        z = float(data.get("accelerometer_z", 0) or 0)
        gyro_x = float(data.get("gyro_x", 0) or 0) - self.offset_gyro_x
        gyro_y = float(data.get("gyro_y", 0) or 0) - self.offset_gyro_y
        gyro_z = float(data.get("gyro_z", 0) or 0) - self.offset_gyro_z

        if self.flat_calibration and self.up_calibration and self.down_calibration and self.left_calibration and self.right_calibration:
            # Calculate lean angles using calibration data
            lean_angle_up = self.calculate_lean_angle(x, y, z, self.flat_calibration, self.up_calibration)
            lean_angle_left = self.calculate_lean_angle(x, y, z, self.flat_calibration, self.left_calibration)
        else:
            lean_angle_up = math.degrees(math.atan2(y, x))
            lean_angle_left = (math.degrees(math.atan2(x, z))-90)*-1

        angular_velocity = math.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)

        force = float(data.get("force", 0) or 0)
        position = float(data.get("position", 0) or 0)
        velocity = float(data.get("velocity", 0) or 0)
        virtual_velocity = float(data.get("virtual_velocity", 0) or 0) * 20
        if virtual_velocity > 100:
            virtual_velocity = 100
        status = data.get("status", "unknown")

        return {
            "lean_angle_up": lean_angle_up,
            "lean_angle_left": lean_angle_left,
            # "angular_velocity": angular_velocity,
            "force": force,
            "position": position,
            "velocity": velocity,
            "virtual_velocity": virtual_velocity, 
            "status": status,
        }

    def calculate_lean_angle(self, x, y, z, flat, target):
        # Use the calibration data to calculate the lean angle
        flat_vector = (flat['x'], flat['y'], flat['z'])
        target_vector = (target['x'], target['y'], target['z'])
        current_vector = (x, y, z)

        flat_length = math.sqrt(sum(coord**2 for coord in flat_vector))
        target_length = math.sqrt(sum(coord**2 for coord in target_vector))
        current_length = math.sqrt(sum(coord**2 for coord in current_vector))

        flat_normalized = tuple(coord / flat_length for coord in flat_vector)
        target_normalized = tuple(coord / target_length for coord in target_vector)
        current_normalized = tuple(coord / current_length for coord in current_vector)

        dot_product = sum(f * c for f, c in zip(flat_normalized, current_normalized))
        angle = math.acos(dot_product) * 180 / math.pi

        return angle

    def enqueue_set_command(self, command):
        self.enqueue_task(self.send_command(command))

    async def send_command(self, command):
        response = await self.loop.run_in_executor(None, lambda: requests.post(f"{self.api_url}/send_command", json=command))
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to send command: {response.status_code}")

    def set_pulse(self, type, duration, strength, frequency):
        command = {
            "command": "SET_PULSE",
            "type": type,
            "duration": int(duration),
            "strength": int(strength),
            "frequency": int(frequency),
        }
        self.enqueue_set_command(command)

    def set_detents(self, type, strength, start_position, step_position, total_steps):
        command = {
            "command": "SET_DETENTS",
            "type": type,
            "strength": int(strength),
            "start_position": float(start_position),
            "step_position": float(step_position),
            "total_steps": int(total_steps),
        }
        self.enqueue_set_command(command)

    def set_force(self, type, strength, start_strength, start_position, saturation_position):
        command = {
            "command": "SET_FORCE",
            "type": type,
            "strength": int(strength),
            "start_strength": int(start_strength),
            "start_position": float(start_position),
            "saturation_position": float(saturation_position),
        }
        self.enqueue_set_command(command)

    def set_mode(self, type):
        command = {
            "command": "SET_MODE",
            "type": type
        }
        self.enqueue_set_command(command)

    def set_row(self, type, damping, gear_ratio, inertia):
        command = {
            "command": "SET_ROW",
            "type": type,
            "damping": int(damping),
            "gear_ratio": int(gear_ratio),
            "inertia": int(inertia),
        }
        self.enqueue_set_command(command)

    async def cleanup(self):
        self.stop_event.set()  # Signal the loop to stop
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        await asyncio.gather(*asyncio.all_tasks(self.loop), return_exceptions=True)
        self.loop.stop()
        self.loop.close()
        print("Controller stopped")

# Example usage
async def main():
    controller = DigitalWeightController(api_url="http://127.0.0.1:8000")

    # Set some commands to enqueue tasks
    controller.set_pulse("type1", 5, 10, 15)
    controller.set_mode("new_mode")

    # Allow some time for tasks to be processed
    await asyncio.sleep(2)

    # Cleanup when done
    await controller.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
