import psutil
import time
from shared.discord import discordError, discordUpdate
# Set the threshold in gigabytes
warning_threshold = 50
error_threshold = 10
last_warning_time = 0


while True:
    # Get available RAM in gigabytes
    available = psutil.virtual_memory().available / (1024 ** 3)

    # Compare with the threshold
    if available <= error_threshold:
        # Send a error
        discordError(
            "Very Low RAM Warning",
            f"Very Low RAM! Available RAM: {available:.2f} GB"
        )
        time.sleep(5*60)
    elif available <= warning_threshold and time.time() - last_warning_time > 5*60:
        # Send a warning only if the last warning was more than 5 minutes ago
        discordUpdate(
            "Low RAM Warning",
            f"Low RAM! Available RAM: {available:.2f} GB"
        )
        last_warning_time = time.time()
        time.sleep(5)
    else:
        # Sleep for some time before checking again
        time.sleep(5)  # Adjust the sleep duration (in seconds) as needed