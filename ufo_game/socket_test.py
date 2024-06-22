import requests
import time

url = "http://127.0.0.1:8000/data"

while True:
    start_time = time.time()
    print(f"Request issued at: {start_time}")
    response = requests.get(url)
    end_time = time.time()
    print(f"Response received at: {end_time}, elapsed time: {end_time - start_time}")
    time.sleep(1)
