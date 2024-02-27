# Scripts

## Installation

### Prerequisites
- Systemd.
- Python 3.x installed.
- Pip package manager.

### Steps
1. Clone the repository (preferably into the home directory):

   ```bash
   git clone https://github.com/westsurname/scripts.git
   ```

2. Navigate to the project directory:

    ```bash
    cd scripts
    ```

3. Install the required packages:

    ```bash 
    pip install -r requirements.txt 
    ```

4. Copy `.env.template` to `.env` and populate the (applicable) variables.


## Blackhole

### Setup

1. Add torrent blackhole download clients to the arrs.

## Import Torrent Folder

### Usage

The script can be run with the following command:

```bash
python3 import_torrent_folder.py
```

The script accepts the following arguments:

- `--directory`: Specifies a specific directory to process.
- `--custom-regex`: Allows you to specify a custom multi-season regex.
- `--dry-run`: If this flag is set, the script will print actions without executing them.
- `--no-confirm`: If this flag is set, the script will execute without asking for confirmation.
- `--radarr`: If this flag is set, the script will use the Radarr symlink directory.
- `--sonarr`: If this flag is set, the script will use the Sonarr symlink directory.
- `--symlink-directory`: Allows you to specify a custom symlink directory.

### Example
Here is an example of how you might use this script:

```bash
python3 import_torrent_folder.py --directory "My TV Show" --radarr --dry-run
```

In this example, the script will process the "My TV Show" directory using the Radarr symlink directory. It will print the actions it would take without actually executing them, because the --dry-run flag is set.


## Delete Non-Linked Folders

### Usage

The script can be run with the following command:

```bash
python3 delete_non_linked_folders.py
```

The script accepts the following arguments:

- `dst_folder`: The destination folder to check for non-linked files. This folder should encompass all folders where symbolic links may exist.
- `--src-folder`: The source folder to check for non-linked files. This is the folder that the symbolic links in the destination folder should point to.
- `--dry-run`: If this flag is provided, the script will only print the non-linked file directories without deleting them.
- `--no-confirm`: If this flag is provided, the script will delete non-linked file directories without asking for confirmation.
- `--only-delete-files`: If this flag is provided, the script will delete only the files in the non-linked directories, not the directories themselves. This is useful for Zurg where directories are automatically removed if they contain no content.

### Warning

This script can potentially delete a large number of files and directories. It is recommended to use the --dry-run flag first to see what the script will delete. Also, make sure to provide the correct source and destination folders, as the script will delete any non-linked files or directories in the destination folder that are not symbolic links to the source folder.

### Example

Here is an example of how you might use this script:

```bash
python3 delete_non_linked_folders.py /path/to/destination/folder --src-folder /path/to/source/folder --dry-run
```

In this example, the script will check the "/path/to/destination/folder" directory againts the "/path/to/source/folder" directory to find directories that are not linked to. It will print the the directories that would be deleted without actually deleting them, because the --dry-run flag is set.