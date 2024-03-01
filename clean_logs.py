import os
import datetime
from shared.shared import pathToScript

folder = os.path.join(pathToScript, "../logs")
max_lines = 1000
max_size = 1048576

for file in os.listdir(folder):
    with open(os.path.join(folder, file), "r") as f:
        line_count = sum(1 for _ in f)

        if line_count > max_lines:
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            f.seek(max(fsize-max_size, 0), 0) 
            lines = f.readlines()[-max_lines:]

            with open(os.path.join(folder, file), "w") as f:
                f.writelines(lines)
            
            print(f"[{datetime.datetime.now()}] Cleaned {file}")
