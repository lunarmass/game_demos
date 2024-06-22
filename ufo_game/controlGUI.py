import tkinter as tk
from tkinter import ttk
import asyncio
import threading
from digitalweight_controller import DigitalWeightController  # Assuming the module is saved as digital_weight_controller.py

class DigitalWeightGUI(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("Digital Weight Controller")
        self.geometry("800x600")

        # self.status_label = ttk.Label(self, text="Status: Starting", font=("Helvetica", 14))
        # self.status_label.pack(pady=10)
        
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(pady=10, fill="x")


        # Add the emergency stop button
        self.emergency_button = tk.Button(self, text="Emergency Stop", command=self.emergency_stop, bg="red", fg="white", font=("Helvetica", 16))
        self.emergency_button.pack(pady=20)
        
        self.create_force_controls()
        self.create_row_controls()
        self.create_pulse_controls()
        # self.create_detents_controls()
        # self.create_mode_controls()

        self.update_button = ttk.Button(self, text="Update Status", command=self.update_status)
        self.update_button.pack(pady=5)

    
        # Create a frame to display the data
        self.data_frame = ttk.Frame(self)
        self.data_frame.pack(pady=10, fill="x")
        self.data_labels = {}

      
      
        self.data_text = tk.Text(self, height=10, width=70, state='disabled')
        self.data_text.pack(pady=10)


        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.update_data_loop()

    def validate_non_negative(self, P):
        return P.isdigit() or P == "" or (P.replace('.', '', 1).isdigit() and P.count('.') < 2)

    def create_pulse_controls(self):
        frame = ttk.LabelFrame(self.controls_frame, text="Set Pulse")
        frame.grid(row=0, column=0, padx=10, pady=10)

        self.pulse_type = tk.StringVar(value="off")
        self.pulse_duration = tk.IntVar(value=5)
        self.pulse_strength = tk.IntVar(value=200)
        self.pulse_frequency = tk.IntVar(value=15)

        vcmd = (self.register(self.validate_non_negative), '%P')

        ttk.Button(frame, text="Set Pulse", command=self.set_pulse).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="Type:").grid(row=1, column=0)
        ttk.Combobox(frame, textvariable=self.pulse_type, values=["off", "on"]).grid(row=1, column=1)

        ttk.Label(frame, text="Duration:").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.pulse_duration, validate='key', validatecommand=vcmd).grid(row=2, column=1)

        ttk.Label(frame, text="Strength:").grid(row=3, column=0)
        ttk.Entry(frame, textvariable=self.pulse_strength, validate='key', validatecommand=vcmd).grid(row=3, column=1)

        ttk.Label(frame, text="Frequency:").grid(row=4, column=0)
        ttk.Entry(frame, textvariable=self.pulse_frequency, validate='key', validatecommand=vcmd).grid(row=4, column=1)

    def create_mode_controls(self):
        frame = ttk.LabelFrame(self.controls_frame, text="Set Mode")
        frame.grid(row=0, column=1, padx=10, pady=10)

        self.mode_type = tk.StringVar(value="off")

        ttk.Button(frame, text="Set Mode", command=self.set_mode).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="Type:").grid(row=1, column=0)
        ttk.Combobox(frame, textvariable=self.mode_type, values=["off", "on"]).grid(row=1, column=1)

    def create_detents_controls(self):
        frame = ttk.LabelFrame(self.controls_frame, text="Set Detents")
        frame.grid(row=0, column=2, padx=10, pady=10)

        self.detents_type = tk.StringVar(value="off")
        self.detents_strength = tk.IntVar(value=100)
        self.detents_start_position = tk.DoubleVar(value=0.0)
        self.detents_step_position = tk.DoubleVar(value=1.0)
        self.detents_total_steps = tk.IntVar(value=10)

        vcmd = (self.register(self.validate_non_negative), '%P')

        ttk.Button(frame, text="Set Detents", command=self.set_detents).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="Type:").grid(row=1, column=0)
        ttk.Combobox(frame, textvariable=self.detents_type, values=["off", "on"]).grid(row=1, column=1)

        ttk.Label(frame, text="Strength:").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.detents_strength, validate='key', validatecommand=vcmd).grid(row=2, column=1)

        ttk.Label(frame, text="Start Position:").grid(row=3, column=0)
        ttk.Entry(frame, textvariable=self.detents_start_position, validate='key', validatecommand=vcmd).grid(row=3, column=1)

        ttk.Label(frame, text="Step Position:").grid(row=4, column=0)
        ttk.Entry(frame, textvariable=self.detents_step_position, validate='key', validatecommand=vcmd).grid(row=4, column=1)

        ttk.Label(frame, text="Total Steps:").grid(row=5, column=0)
        ttk.Entry(frame, textvariable=self.detents_total_steps, validate='key', validatecommand=vcmd).grid(row=5, column=1)

    def create_force_controls(self):
        frame = ttk.LabelFrame(self.controls_frame, text="Set Force")
        frame.grid(row=0, column=3, padx=10, pady=10)

        self.force_type = tk.StringVar(value="linear")
        self.force_strength = tk.IntVar(value=100)
        self.force_start_strength = tk.IntVar(value=20)
        self.force_start_position = tk.DoubleVar(value=0)
        self.force_saturation_position = tk.DoubleVar(value=2)

        vcmd = (self.register(self.validate_non_negative), '%P')

        ttk.Button(frame, text="Set Force", command=self.set_force).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="Type:").grid(row=1, column=0)
        ttk.Combobox(frame, textvariable=self.force_type, values=["off", "constant", "linear"]).grid(row=1, column=1)

        ttk.Label(frame, text="Strength:").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.force_strength, validate='key', validatecommand=vcmd).grid(row=2, column=1)

        ttk.Label(frame, text="Start Strength:").grid(row=3, column=0)
        ttk.Entry(frame, textvariable=self.force_start_strength, validate='key', validatecommand=vcmd).grid(row=3, column=1)

        ttk.Label(frame, text="Start Position:").grid(row=4, column=0)
        ttk.Entry(frame, textvariable=self.force_start_position, validate='key', validatecommand=vcmd).grid(row=4, column=1)

        ttk.Label(frame, text="Saturation Position:").grid(row=5, column=0)
        ttk.Entry(frame, textvariable=self.force_saturation_position, validate='key', validatecommand=vcmd).grid(row=5, column=1)

    def create_row_controls(self):
        frame = ttk.LabelFrame(self.controls_frame, text="Set Row")
        frame.grid(row=0, column=4, padx=10, pady=10)

        self.row_type = tk.StringVar(value="off")
        self.row_damping = tk.IntVar(value=20)
        self.row_gear_ratio = tk.IntVar(value=5)
        self.row_inertia = tk.IntVar(value=1)

        vcmd = (self.register(self.validate_non_negative), '%P')

        ttk.Button(frame, text="Set Row", command=self.set_row).grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="Type:").grid(row=1, column=0)
        ttk.Combobox(frame, textvariable=self.row_type, values=["off", "on"]).grid(row=1, column=1)

        ttk.Label(frame, text="Damping:").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.row_damping, validate='key', validatecommand=vcmd).grid(row=2, column=1)

        ttk.Label(frame, text="Gear Ratio:").grid(row=3, column=0)
        ttk.Entry(frame, textvariable=self.row_gear_ratio, validate='key', validatecommand=vcmd).grid(row=3, column=1)

        ttk.Label(frame, text="Inertia:").grid(row=4, column=0)
        ttk.Entry(frame, textvariable=self.row_inertia, validate='key', validatecommand=vcmd).grid(row=4, column=1)

    def set_pulse(self):
        self.controller.set_pulse(
            self.pulse_type.get(),
            self.pulse_duration.get(),
            self.pulse_strength.get(),
            self.pulse_frequency.get()
        )

    def set_mode(self):
        self.controller.set_mode(self.mode_type.get())

    def set_detents(self):
        self.controller.set_detents(
            self.detents_type.get(),
            self.detents_strength.get(),
            self.detents_start_position.get(),
            self.detents_step_position.get(),
            self.detents_total_steps.get()
        )

    def set_force(self):
        self.controller.set_force(
            self.force_type.get(),
            self.force_strength.get(),
            self.force_start_strength.get(),
            self.force_start_position.get(),
            self.force_saturation_position.get()
        )

    def set_row(self):
        self.controller.set_row(
            self.row_type.get(),
            self.row_damping.get(),
            self.row_gear_ratio.get(),
            self.row_inertia.get()
        )

    def emergency_stop(self):
        self.controller.set_force(
            "off",
            0,
            0,
            0.0,
            0.0
        )

    def update_status(self):
        status = self.controller.get_status()
        self.status_label.config(text=f"Status: {status}")

    def update_data_loop(self):
        if not self.controller.busy:
            self.controller.enqueue_task(self.controller.get_controller_data())
        self.after(1000, self.display_data)  # Check for new data every second

    def display_data(self):
        if not self.controller.data_queue.empty():
            data = self.controller.data_queue.get_nowait()
            self.data_text.config(state='normal')
            self.data_text.delete(1.0, tk.END)
            self.data_text.insert(tk.END, str(data))
            self.data_text.config(state='disabled')
            
            for key, value in data.items():
                if key not in self.data_labels:
                    label = ttk.Label(self.data_frame, text=f"{key}: {value}")
                    label.pack(anchor="w")
                    self.data_labels[key] = label
                else:
                    self.data_labels[key].config(text=f"{key}: {value}")

        self.update_data_loop()

    def on_closing(self):
        asyncio.run_coroutine_threadsafe(self.controller.cleanup(), self.loop)
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        self.loop.close()
        self.destroy()

if __name__ == "__main__":
    api_url = "http://127.0.0.1:8000"
    controller = DigitalWeightController(api_url)
    gui = DigitalWeightGUI(controller)
    gui.mainloop()
