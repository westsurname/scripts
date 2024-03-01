import glob
import os
import shutil

mount_path = '/path/to/mount'
files = glob.glob(f'{mount_path}/**/*.rclonelink', recursive=True)
print(files)

for file in files:
    with open(file, 'r') as f:
        src = f.read()
        dest = file.replace('.rclonelink', '')
    print(f"{dest} -> {src}")
    os.remove(file)
    shutil.copyfile(src, dest)