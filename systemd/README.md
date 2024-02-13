# Blackhole Systemd Setup

## Installation

1. Copy the files in this repository into the systemd folder on your system.

    ```bash
    cp *.service *.path /etc/systemd/system/
    ```

2. Update the `PathExistsGlob` in `blackhole-sonarr.path` and `blackhole-radarr.path` to point to their respective Arr (Sonarr or Radarr) blackhole torrent folder.

3. Update the `blackhole@.service` file to point to the location of this repository if it's not in the home folder.

## Usage

Start the services using the following commands:

- For Sonarr:

    ```bash
    systemctl start blackhole@sonarr.service
    ```

- For Radarr:

    ```bash
    systemctl start blackhole@radarr.service
    ```

Enable the services to start on boot:

- For Sonarr:

    ```bash
    systemctl enable blackhole@sonarr.service
    ```

- For Radarr:

    ```bash
    systemctl enable blackhole@radarr.service
    ```

Note: Depending on your system setup, you may need to add `sudo` or `--user` to systemd commands.