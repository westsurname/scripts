import requests
from shared.shared import plexHeaders, plex

def getServerToken(token):
    response = requests.get(f"{plex['host']}/api/v2/resources?X-Plex-Token={token}", headers=plexHeaders)
    resources = response.json()
    server_token = next(resource['accessToken'] for resource in resources if resource['clientIdentifier'] == plex['serverMachineId'])
    return server_token