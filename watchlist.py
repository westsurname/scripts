import traceback
import requests
import json
import datetime
from typing import List
from shared.discord import discordError, discordUpdate
from shared.shared import plex, plexHeaders, tokensFilename
from shared.overseerr import requestItem, getUserForPlexToken
import xml.etree.ElementTree as ET

host = plex['host']
metadataHost = plex['metadataHost']
serverHost = plex['serverHost']
serverMachineId = plex['serverMachineId']


class SeasonMetadata:
    def __init__(self, json) -> None:
        self.viewedLeafCount = json['viewedLeafCount']
        self.leafCount = json['leafCount']
        self.index = json['index']


def getSeasonsMetadata(ratingKey, headers) -> List[SeasonMetadata]:
    # excludeAllLeaves=1?
    seasonsMetadataRequest = requests.get(f"{metadataHost}library/metadata/{ratingKey}/children?excludeAllLeaves=1&includeUserState=1", headers=headers)
    seasonsMetadata = seasonsMetadataRequest.json()['MediaContainer']['Metadata']

    return list(map(SeasonMetadata, seasonsMetadata))


def getServerSeasonsMetadata(ratingKey, headers, owner) -> List[SeasonMetadata]:
    headers = getServerHeaders(headers, owner)

    serverMetadataInfoRequest = requests.get(f"{serverHost}/library/all?type=2&guid=plex%3A%2F%2Fshow%2F{ratingKey}", headers=headers)
    serverMetadataInfo = serverMetadataInfoRequest.json()['MediaContainer']

    if 'Metadata' in serverMetadataInfo:
        serverMetadata = serverMetadataInfo['Metadata']
        showServerMetadata = next(iter(serverMetadata), None)

        if showServerMetadata:
            serverRatingKey = showServerMetadata['ratingKey']
            serverSeasonsMetadataRequest = requests.get(f"{serverHost}/library/metadata/{serverRatingKey}/children", headers=headers)
            serverSeasonsMetadata = serverSeasonsMetadataRequest.json()['MediaContainer']['Metadata']

            return list(map(SeasonMetadata, serverSeasonsMetadata))

    return


def getCombinedSeasonsMetadata(ratingKey, headers, owner) -> List[SeasonMetadata]:
    seasonsMetadata = getSeasonsMetadata(ratingKey, headers)
    serverSeasonsMetadata = getServerSeasonsMetadata(ratingKey, headers, owner)

    if not serverSeasonsMetadata: return seasonsMetadata

    combinedSeasonsMetadata = []

    for seasonMetadata in seasonsMetadata:
        serverSeasonMetadata = next(iter(serverSeasonMetadata for serverSeasonMetadata in serverSeasonsMetadata if serverSeasonMetadata.index == seasonMetadata.index), None)

        combinedSeasonMetadata = combineSeasonMetadata(seasonMetadata, serverSeasonMetadata)
        combinedSeasonsMetadata.append(combinedSeasonMetadata)

    return combinedSeasonsMetadata


def combineSeasonMetadata(seasonMetadata: SeasonMetadata, serverSeasonMetadata: SeasonMetadata) -> SeasonMetadata:
    if serverSeasonMetadata and serverSeasonMetadata.viewedLeafCount > seasonMetadata.viewedLeafCount:
        seasonMetadata.viewedLeafCount = serverSeasonMetadata.viewedLeafCount

    return seasonMetadata


def getServerHeaders(headers, owner):
    if owner: return headers

    usersRequest = requests.get(f"{host}api/users", headers=headers)
    users = ET.fromstring(usersRequest.content)

    servers = (server.attrib for user in users for server in user)
    serverId = next(server['id'] for server in servers if server['machineIdentifier'] == serverMachineId)

    serverRequest = requests.get(f"{host}api/servers/{serverMachineId}/shared_servers/{serverId}", headers=headers)
    serverToken = ET.fromstring(serverRequest.content)[0].attrib['accessToken']

    return {
        **headers,
        'X-Plex-Token': serverToken
    }


def buildRecentItem(item):
    return f"{item['ratingKey']}:{item['watchlistedAt']}"


def getCurrentSeason(ratingKey, headers, token):
    season = [1]

    seasonsMetadata = getCombinedSeasonsMetadata(ratingKey, headers, token.get('owner', False))

    # Consider logic for choosing the season
    for seasonMetadata in reversed(seasonsMetadata):
        totalCount = seasonMetadata.leafCount
        remainingCount = totalCount - seasonMetadata.viewedLeafCount
        if remainingCount <= 0 and totalCount != 0 and seasonMetadata != seasonsMetadata[-1]:
            season = [seasonMetadata.index + 1]
            break
        elif remainingCount < totalCount:
            season = [seasonMetadata.index]
            break

    return season


def getWatchlistedAt(ratingKey, headers):
    request = requests.get(f"{metadataHost}library/metadata/{ratingKey}/userState", headers=headers)

    if request.status_code != 200: return
    
    watchlistedAt = request.json()['MediaContainer']['UserState']['watchlistedAt']
    
    return watchlistedAt

def run():
    print()
    print(datetime.datetime.now())
    print('Running Watchlist')

    with open(tokensFilename, 'r') as tokensFile:
        tokens = json.load(tokensFile)

    for userId, token in tokens.items():
        try:
            headers = {
                **plexHeaders,
                'X-Plex-Token': token['token']
            }

            def requestWatchlist(tryAgain=True):
                try:
                    return requests.get(
                    f"{metadataHost}library/sections/watchlist/all?includeFields=ratingKey%2CwatchlistedAt&sort=watchlistedAt%3Adesc",
                    headers={
                        **headers,
                        'If-None-Match': token['etag'],
                    })   
                except:
                    if tryAgain:
                        return requestWatchlist(tryAgain=False)
                    else:
                        raise

            watchlistRequest = requestWatchlist()

            if watchlistRequest.status_code == 401:
                print(f"UserId {userId} no longer authenticated")
                discordError(f"UserId {userId} no longer authenticated")
                continue

            if watchlistRequest.status_code == 304:
                print(f"No changes for userId {userId}")
                continue

            if watchlistRequest.status_code != 200:
                print(watchlistRequest)
                print(watchlistRequest.url)
                continue

            etag = watchlistRequest.headers['etag']

            now = datetime.datetime.now()
            recentlyProcessedItems = token.get('recentlyProcessedItems', [])

            watchlist = watchlistRequest.json()['MediaContainer']

            if not 'Metadata' in watchlist:
                continue

            watchlistItems = watchlist['Metadata']

            recentWatchlist = []
            newRecentlyProcessedItems = []

            for item in watchlistItems:
                try:
                    watchlistedAt = datetime.datetime.fromtimestamp(item['watchlistedAt'])
                    discordUpdate('Watchlist has resumed functioning')
                except:
                    ratingKey = item['ratingKey']
                    watchlistedAtTimestamp = getWatchlistedAt(ratingKey, headers)

                    if not watchlistedAtTimestamp:
                        print(f"No watchlisted timestamp for RatingKey {ratingKey} and UserId {userId}")
                        discordError(f"No watchlisted timestamp for RatingKey {ratingKey} and UserId {userId}")
                        continue

                    watchlistedAt = datetime.datetime.fromtimestamp(watchlistedAtTimestamp)
                    item['watchlistedAt'] = watchlistedAtTimestamp

                if now - watchlistedAt < datetime.timedelta(hours=1):
                    recentItem = buildRecentItem(item)
                    newRecentlyProcessedItems.append(recentItem)

                    if not recentItem in recentlyProcessedItems:
                        recentWatchlist.append(item)
                else:
                    break

            with open(tokensFilename, 'r+') as tokensFile:
                tokens = json.load(tokensFile)
                token = tokens[userId]
                token['etag'] = etag
                token['recentlyProcessedItems'] = newRecentlyProcessedItems
                tokensFile.seek(0)
                json.dump(tokens, tokensFile)
                tokensFile.truncate()

            user = getUserForPlexToken(token['token'])
            userId = user['id']
            username = user['displayName']

            print(f"Requesting new items for userId {userId} - {username}")

            if not recentWatchlist:
                print("No new items were found")

            for item in recentWatchlist:
                ratingKey = item['ratingKey']
                watchlistedAt = item['watchlistedAt']
                requestItem(user, ratingKey, watchlistedAt, headers, getSeason=lambda: getCurrentSeason(ratingKey, headers, token))

        except:
            e = traceback.format_exc()

            print(f"Error processing requests for userId {userId}")
            print(e)

            discordError(f"Error processing requests for userId {userId}", e)

if __name__ == "__main__":
    run()