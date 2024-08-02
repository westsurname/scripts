import json
import traceback
import requests
import datetime
from shared.discord import discordError, discordUpdate
from shared.shared import plex, overseerr, overseerrHeaders, tokensFilename

host = plex['host']
metadataHost = plex['metadataHost']


def getUserForPlexToken(token):
    userRequest = requests.post(f"{overseerr['host']}/api/v1/auth/plex", json={'authToken': token}, headers=overseerrHeaders)
    user = userRequest.json()

    return user

def getUserForPlexServerToken(serverToken):
    with open(tokensFilename, 'r') as tokensFile:
        tokens = json.load(tokensFile).values()
        token = next((token['token'] for token in tokens if token['serverToken'] == serverToken), plex['serverApiKey'])

        return getUserForPlexToken(token)

def requestItem(user, ratingKey, watchlistedAtTimestamp, metadataHeaders, getSeason):
    try:
        userId = user['id']
        username = user['displayName']

        watchlistedAt = datetime.datetime.fromtimestamp(watchlistedAtTimestamp)

        metadataRequest = requests.get(f"{metadataHost}library/metadata/{ratingKey}", headers=metadataHeaders)
        metadata = next(iter(metadataRequest.json()['MediaContainer']['Metadata']), None)

        if not metadata:
            print(f"No metadata found for ratingKey {ratingKey}")
            return

        now = datetime.datetime.now()
        timespan = now - watchlistedAt
       
        tmdbId = next(guid[len('tmdb://'):] for guid in (item['id'] for item in metadata['Guid']) if
                      guid.startswith('tmdb://'))

        data = {
            'mediaType': 'movie' if metadata['type'] == 'movie' else 'tv',
            'userId': userId,
            'mediaId': int(tmdbId),
        }

        if metadata['type'] == 'show':
            data['seasons'] = getSeason()

        requestRequest = requests.post(f"{overseerr['host']}/api/v1/request", json=data, headers=overseerrHeaders)
        print(f"{metadata['title']} - {str(timespan)} - Requested")

    except:
        e = traceback.format_exc()

        print(f"Error processing request {ratingKey} for userId {userId} - {username}")
        print(e)

        discordError(f"Error processing request {ratingKey} for userId {userId} - {username}", e)