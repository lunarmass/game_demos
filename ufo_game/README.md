## Running the UFO Game

To run the UFO game, execute the following command in your terminal:

```bash
python ufo_game.py
```

# Running the UFO Game with the Digital Weight Device

## Connecting the Digital Weight Device

### Steps to Connect

1. **Connect the Device via USB**:

   - Use a USB isolator to connect the device to your host computer.
   - Ensure the device is powered on before connecting.

2. **Start the Digital Weight Socket**:

   - Execute the following command to start the socket:
     ```bash
     python digitalweight_socket.py
     ```

3. **Set the Global Constant**:

   - In your code, ensure the global constant is set to use the digital weight controller:
     ```python
     USE_DIGITAL_WEIGHT_CONTROLLER = True
     ```

4. **Start the UFO Game**:
   - Run the UFO game as mentioned earlier:
     ```bash
     python ufo_game.py
     ```

## Additional Monitoring

While the UFO game is running, you can also start the digital weight controller to send serial commands to the device and monitor the output. Use the following command:

```bash
python digitalweight_controller.py
```
