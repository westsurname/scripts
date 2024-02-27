FROM python:3.8-slim

# Define build-time variable and set environment variable
ARG BLACKHOLE_RD_MOUNT_TORRENTS_PATH_HOST
ENV BLACKHOLE_RD_MOUNT_TORRENTS_PATH=$BLACKHOLE_RD_MOUNT_TORRENTS_PATH_HOST

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

# Copy and then replace placeholder in blackhole@.service with actual path
COPY systemd/blackhole@.service /etc/systemd/system/blackhole@.service
RUN sed -i 's|%h/scripts|/app|g' /etc/systemd/system/blackhole@.service

# Copy and then replace placeholder in blackhole-radarr.path with actual path
COPY systemd/blackhole-radarr.path /etc/systemd/system/blackhole-radarr.path
RUN sed -i 's|%h/path/to/radarr/blackhole/torrent/folder|'"${BLACKHOLE_RD_MOUNT_TORRENTS_PATH}"'|g' /etc/systemd/system/blackhole-radarr.path

# Copy and then replace placeholder in blackhole-sonarr.path with actual path
COPY systemd/blackhole-sonarr.path /etc/systemd/system/blackhole-sonarr.path
RUN sed -i 's|%h/path/to/sonarr/blackhole/torrent/folder|'"${BLACKHOLE_RD_MOUNT_TORRENTS_PATH}"'|g' /etc/systemd/system/blackhole-sonarr.path

# Set working directory
WORKDIR /app

# Enable the systemd services for automatic start
RUN systemctl enable blackhole-radarr.path
RUN systemctl enable blackhole-sonarr.path

# Set stop signal for systemd
STOPSIGNAL SIGRTMIN+3

# Command to start systemd
CMD ["/lib/systemd/systemd"]