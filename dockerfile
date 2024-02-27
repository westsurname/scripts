FROM python:3.8-slim

# Define build-time variable
ARG BLACKHOLE_RD_MOUNT_TORRENTS_PATH

# Install systemd and other utilities
RUN apt-get update && apt-get install -y systemd systemd-sysv && rm -rf /var/lib/apt/lists/*

# Remove unnecessary systemd services
RUN find /etc/systemd/system \
         /lib/systemd/system \
         -path '*.wants/*' \
         -not -name '*journald*' \
         -not -name '*systemd-tmpfiles*' \
         -not -name '*systemd-user-sessions*' \
         -delete

COPY . /app/
RUN rm -rf /app/systemd

# Install Python dependencies
RUN pip install -r /app/requirements.txt

# Replace placeholder in blackhole@.service with actual path before copying
RUN sed -i 's|%h/scripts|/app|g' blackhole@.service && \
    COPY blackhole@.service /etc/systemd/system/blackhole@.service

# Replace placeholder in blackhole-radarr.path with actual path before copying
RUN sed -i 's|%h/path/to/radarr/blackhole/torrent/folder|'"${BLACKHOLE_RD_MOUNT_TORRENTS_PATH}"'|g' blackhole-radarr.path && \
    COPY blackhole-radarr.path /etc/systemd/system/blackhole-radarr.path

# Replace placeholder in blackhole-sonarr.path with actual path before copying
RUN sed -i 's|%h/path/to/sonarr/blackhole/torrent/folder|'"${BLACKHOLE_RD_MOUNT_TORRENTS_PATH}"'|g' blackhole-sonarr.path && \
    COPY blackhole-sonarr.path /etc/systemd/system/blackhole-sonarr.path

# Set working directory
WORKDIR /app

# Enable the systemd services for automatic start
RUN systemctl enable blackhole-radarr.path
RUN systemctl enable blackhole-sonarr.path

# Set stop signal for systemd
STOPSIGNAL SIGRTMIN+3

# Command to start systemd
CMD ["/lib/systemd/systemd"]