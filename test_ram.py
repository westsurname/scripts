import psutil
import time

def test_ram_allocation():
    for i in range(50):
        size = (i + 1) * 100 * 1024 * 1024  # 100 MB increments
        print(f"Allocating {size / (1024 * 1024)} MB of RAM")
        data = " " * size  # Allocate memory by using a string
        time.sleep(1)  # Sleep for 1 second to observe memory usage
        ram_info = psutil.virtual_memory()
        print(f"Available RAM: {ram_info.available / (1024 * 1024 * 1024)} GB, Used RAM: {ram_info.used / (1024 * 1024 * 1024)} GB")
        del data  # Free the memory

test_ram_allocation()