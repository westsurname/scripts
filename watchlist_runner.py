import time
from watchlist import run

if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception as e:
            print(f"An error occurred: {e}")
        time.sleep(60)