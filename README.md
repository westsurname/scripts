# Scripts

## Installation

### Prerequisites
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
4. Copy `.env.template` to `.env` and populate the (applicable) variables:

   - **Server**:
     - `SERVER_DOMAIN`: The domain name of your server.

   - **Plex** - Watchlist, Plex Authentication, Plex Request, Plex Refresh:
     - `PLEX_HOST`: The URL to general Plex services.
     - `PLEX_METADATA_HOST`: The URL to the Plex metadata service.
     - `PLEX_SERVER_HOST`: The host address of your Plex server.
     - `PLEX_SERVER_MACHINE_ID`: The unique machine identifier for your Plex server.
     - `PLEX_SERVER_API_KEY`: Your Plex server's API key for authentication.
     - `PLEX_SERVER_MOVIE_LIBRARY_ID`: The library ID for movies on your Plex server.
     - `PLEX_SERVER_TV_SHOW_LIBRARY_ID`: The library ID for TV shows on your Plex server.

   - **Overseerr** - Watchlist, Plex Authentication, Plex Request, Reclaim Space:
     - `OVERSEERR_HOST`: The host address of your Overseeer instance.
     - `OVERSEERR_API_KEY`: The API key for accessing Overseeer.

   - **Sonarr** - Blackhole, Repair, Move Media to Directory, Reclaim Space, Add Next Episode:
     - `SONARR_HOST`: The host address of your Sonarr instance.
     - `SONARR_API_KEY`: The API key for accessing Sonarr.
     - `SONARR_ROOT_FOLDER`: The root folder path for Sonarr media files. (Required for repair compose service only)

   - **Radarr** - Blackhole, Repair, Move Media to Directory, Reclaim Space:
     - `RADARR_HOST`: The host address of your Radarr instance.
     - `RADARR_API_KEY`: The API key for accessing Radarr.
     - `RADARR_ROOT_FOLDER`: The root folder path for Radarr media files. (Required for repair compose service only)

   - **Tautulli** - Reclaim Space:
     - `TAUTULLI_HOST`: The host address of your Tautulli instance.
     - `TAUTULLI_API_KEY`: The API key for accessing Tautulli.

   - **RealDebrid** - Blackhole, Repair:
     - `REALDEBRID_ENABLED`: Set to `true` to enable RealDebrid services.
     - `REALDEBRID_HOST`: The host address for the RealDebrid API.
     - `REALDEBRID_API_KEY`: The API key for accessing RealDebrid services.
     - `REALDEBRID_MOUNT_TORRENTS_PATH`: The path to the RealDebrid mount torrents folder.

   - **TorBox** - Blackhole, Repair:
     - `TORBOX_ENABLED`: Set to `true` to enable TorBox services.
     - `TORBOX_HOST`: The host address for the TorBox API.
     - `TORBOX_API_KEY`: The API key for accessing TorBox services.
     - `TORBOX_MOUNT_TORRENTS_PATH`: The path to the TorBox mount torrents folder.

   - **Trakt** - Reclaim Space:
     - `TRAKT_API_KEY`: The API key for integrating with Trakt.

   - **Watchlist** - Watchlist, Plex Request:
     - `WATCHLIST_PLEX_PRODUCT`: Identifier for the Plex product used in watchlists.
     - `WATCHLIST_PLEX_VERSION`: The version of the Plex product used.
     - `WATCHLIST_PLEX_CLIENT_IDENTIFIER`: A unique identifier for the Plex client.

   - **Blackhole** - Blackhole:
     - `BLACKHOLE_BASE_WATCH_PATH`: The base path for watched folders by the blackhole mechanism. Can be relative or absolute.
     - `BLACKHOLE_RADARR_PATH`: The path where torrent files will be dropped into by Radarr, relative to the base path.
     - `BLACKHOLE_SONARR_PATH`: The path where torrent files will be dropped into by Sonarr, relative to the base path.
     - `BLACKHOLE_FAIL_IF_NOT_CACHED`: Whether to fail operations if content is not cached.
     - `BLACKHOLE_RD_MOUNT_REFRESH_SECONDS`: How long to wait for the RealDebrid mount to refresh in seconds.
     - `BLACKHOLE_WAIT_FOR_TORRENT_TIMEOUT`: The timeout in seconds to wait for a torrent to be successful before failing.
     - `BLACKHOLE_HISTORY_PAGE_SIZE`: The number of history items to pull at once when attempting to mark a download as failed.

   - **Plex Request** - Plex Request:
     - `PLEX_REQUEST_SSL_PATH` (Optional): The path to SSL certificates for Plex Request. If provided, this directory should contain the following files:
       - `fullchain.pem`: The full certificate chain file.
       - `privkey.pem`: The private key file.
       - `chain.pem`: The certificate chain file.
       - `dhparam.pem`: The Diffie-Hellman parameters file.

   - **Discord** - Blackhole, Watchlist, Plex Authentication, Plex Request, Monitor Ram, Reclaim Space:
     - `DISCORD_ENABLED`: Set to `true` to enable Discord error notifications.
     - `DISCORD_UPDATE_ENABLED`: Set to `true` to enable update notifications as well on Discord.
     - `DISCORD_WEBHOOK_URL`: The Discord webhook URL for sending notifications.

   - **Repair** - Repair:
     - `REPAIR_REPAIR_INTERVAL`: The interval in smart format (e.g., '1h2m3s') to wait between repairing each media file.
     - `REPAIR_RUN_INTERVAL`: The interval in smart format (e.g., '1w2d3h4m5s') to run the repair process.

   - **General Configuration**:
    - `PYTHONUNBUFFERED`: Set to `TRUE` to ensure Python output is displayed in the logs in real-time.
    - `PUID`: Set this to the user ID that the service should run as.
    - `PGID`: Set this to the group ID that the service should run as.
    - `UMASK`: Set this to control the default file creation permissions.
    - `DOCKER_NETWORK`: Set this to the name of the Docker network to be used by the services.
    - `DOCKER_NETWORK_EXTERNAL`: Set this to `true` if specifying an external Docker network above, otherwise set to `false`.
    
## Blackhole

### Setup

1. Within the arrs, navigate to `Settings > Download Clients` and add a `Torrent Blackhole` client.

2. Configure the torrent blackhole download client as follows:
   - **Name**: `blackhole`
   - **Enable**: Yes
   - **Torrent Folder**: Set to `[BLACKHOLE_BASE_WATCH_PATH]/[BLACKHOLE_RADARR_PATH]` for Radarr or `[BLACKHOLE_BASE_WATCH_PATH]/[BLACKHOLE_SONARR_PATH]` for Sonarr
   - **Watch Folder**: Set to `[Torrent Folder]/completed`
   - **Save Magnet Files**: Yes, with the extension `.magnet`
   - **Read Only**: No
   - **Client Priority**: Prioritize as you please
   - **Tags**: Tag as you please
   - **Completed Download Handling**: Remove Completed

3. Run the `python_watcher.py` script to start monitoring the blackhole:

    ```bash
    python3 python_watcher.py
    ```

## Repair

### Usage

The repair script can be run with the following command:

```bash
python3 repair.py
```
The script accepts the following arguments:

- `--dry-run`: Perform a dry run without making any changes.
- `--no-confirm`: Execute without confirmation prompts.
- `--repair-interval`: Optional interval in smart format (e.g., '1h2m3s') to wait between repairing each media file.
- `--run-interval`: Optional interval in smart format (e.g., '1w2d3h4m5s') to run the repair process.
- `--mode`: Choose repair mode: `symlink` or `file`. `symlink` to repair broken symlinks and `file` to repair missing files. (default: 'symlink').
- `--include-unmonitored`: Include unmonitored media in the repair process.

### Warning
This script can potentially delete and re-download a large number of files. It is recommended to use the `--dry-run` flag first to see what actions the script will take.

### Example

Here's an example of how you might use this script:

```bash
python3 repair.py --mode file --repair-interval 30m --run-interval 1d --dry-run
```

In this example, the script will run in 'file' mode, waiting 30 minutes between each repair and running once a day. It will perform a dry run, printing actions without executing them.


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
python3 import_torrent_folder.py --directory "Some Movie (2024)" --radarr --dry-run
```

In this example, the script will process the "Some Movie (2024)" directory using the Radarr symlink directory. It will print the actions it would take without actually executing them, because the --dry-run flag is set.


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