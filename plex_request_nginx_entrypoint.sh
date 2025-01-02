#!/bin/sh

# Function to find the Plex certificate
find_plex_cert() {
    find /plex/Cache -name "cert-v2.p12" 2>/dev/null | head -n 1
}

# Function to process the certificate
process_certificate() {
    echo "Starting certificate processing..."
    mkdir -p /ssl
    
    # Find the certificate path
    PLEX_CERT=$(find_plex_cert)
    echo "Found certificate at: ${PLEX_CERT}"
    
    if [ -z "$PLEX_CERT" ]; then
        echo "Error: Could not find cert-v2.p12 in the Plex Media Server/Cache directory"
        return 1
    fi
    
    # Generate the password from the machine ID
    echo "Generating certificate password..."
    CERT_PASS=$(echo -n "plex${PLEX_SERVER_MACHINE_ID}" | openssl dgst -sha512 | cut -d' ' -f2)
    
    # Extract private key
    echo "Extracting private key..."
    if ! openssl pkcs12 -in "${PLEX_CERT}" -nodes -passin "pass:${CERT_PASS}" -out "/ssl/key.pem" -nocerts 2>&1; then
        echo "Error extracting private key"
        return 1
    fi
    
    # Extract certificate chain
    echo "Extracting certificate chain..."
    if ! openssl pkcs12 -in "${PLEX_CERT}" -passin "pass:${CERT_PASS}" -out "/ssl/fullchain.pem" -nokeys 2>&1; then
        echo "Error extracting certificate chain"
        return 1
    fi
    
    # Set proper permissions
    echo "Setting file permissions..."
    chmod 600 "/ssl/key.pem"
    chmod 644 "/ssl/fullchain.pem"
    
    # Verify the certificate files exist and have content
    if [ -s "/ssl/key.pem" ] && [ -s "/ssl/fullchain.pem" ]; then
        echo "Certificate files generated successfully:"
        ls -l /ssl/key.pem /ssl/fullchain.pem
    else
        echo "Error: Certificate files are empty or missing"
        return 1
    fi
    
    echo "Certificate processing completed successfully"
}

# Initial certificate processing
process_certificate || exit 1

# Get the initial certificate path for monitoring
PLEX_CERT=$(find_plex_cert)

# Function to watch for certificate changes
watch_certificates() {
    while inotifywait -e modify,create,move "$(dirname "${PLEX_CERT}")"; do
        echo "Changes detected in certificate directory, checking certificate..."
        NEW_CERT=$(find_plex_cert)
        if [ "$NEW_CERT" != "$PLEX_CERT" ]; then
            echo "Certificate path changed from ${PLEX_CERT} to ${NEW_CERT}"
            PLEX_CERT=$NEW_CERT
        fi
        process_certificate
        # Reload nginx to pick up the new certificates
        nginx -s reload
    done
}

# Start the certificate monitoring in the background, but redirect output to main process
watch_certificates &
WATCH_PID=$!

# Save the PID to a file for management
echo $WATCH_PID > /var/run/cert-watch.pid