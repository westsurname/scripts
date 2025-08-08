import asyncio
from datetime import datetime
import os
from threading import Thread
import traceback
import re
import requests
import json
import uuid
import websockets
import declxml as xml
from flask import Flask, jsonify, request, Response
from flask_caching import Cache
from flask_sock import Sock
from websockets.asyncio.client import connect
from shared.discord import discordError, discordUpdate
from shared.shared import plex, plexHeaders, pathToScript
from shared.overseerr import requestItem, getUserForPlexServerToken
from werkzeug.routing import BaseConverter, ValidationError

mediaTypeNums = {
    "movie": "1",
    "show": "2",
    "season": "3",
    "episode": "4"
}

class MetadataRatingKeyConverter(BaseConverter):
    regex = '[0-9a-fA-F]{24}'

    def to_python(self, value):
        if re.match(self.regex, value):
            return value
        raise ValidationError()

    def to_url(self, value):
        return value
    
class PlexWebSocketMiddleware:
    def __init__(self):
        self.clients = set()
        self.plexWs = None
        
    async def addClient(self, ws):
        self.clients.add(ws)
        if not self.plexWs:
            # Connect to real Plex server WebSocket using same path and query params
            path = ws.environ.get('RAW_URI')
            wsUrl = re.sub(r'^http(s)?://', lambda m: f'ws{m.group(1) or ""}://', plex['serverHost'])
            
            print('connecting')
            self.plexWs = await connect(
                f"{wsUrl}{path}",
                additional_headers={
                    key[5:].replace('_', '-').lower(): value
                    for key, value in ws.environ.items()
                    if key.startswith('HTTP_')
                }
            )
            print('connected')
            # Start forwarding Plex messages
            await asyncio.create_task(self.forwardPlexMessages())

    async def removeClient(self, ws):
        self.clients.remove(ws)
        if not self.clients and self.plexWs:
            await self.plexWs.close()
            self.plexWs = None

    async def forwardPlexMessages(self):
        try:
            print('forwarding all messages')
            async for message in self.plexWs:
                print('forwarding message')
                print(message)
                await self.broadcast(message)
        except websockets.exceptions.ConnectionClosed:
            print('connection closed')
            self.plexWs = None

    async def broadcast(self, message):
        if self.clients:
            deadClients = set()
            for client in self.clients:
                try:
                    client.send(message)
                except Exception as e:
                    print('dead client')
                    print(e)
                    deadClients.add(client)
            # Clean up dead connections
            for dead in deadClients:
                await self.removeClient(dead)

    async def injectNotification(self, message):
        print('injecting notification')
        print(message)
        await self.broadcast(json.dumps(message))

# Instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
app.url_map.strict_slashes = False
app.url_map.converters['metadataRatingKey'] = MetadataRatingKeyConverter

# Set up caching
cacheDir = os.path.join(pathToScript, "../cache")
for file in os.listdir(cacheDir):
    filePath = os.path.join(cacheDir, file)
    try:
        if os.path.isfile(filePath):
            os.unlink(filePath)
    except Exception as e:
        print(e)

cache = Cache(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DEFAULT_TIMEOUT': 300, 'CACHE_DIR': cacheDir})

_print = print

def print(*values: object):
    _print(f"[{datetime.now()}]", *values, flush=True)

def processDict(key, value):
    return xml.dictionary(key, [*traverseDict(value, processDict, processList, processElse)], required=False)

def processList(key, value):
    if any(value):
        alias = 'Metadata' if key == 'Metadata' else None
        key = 'Video' if key == 'Metadata' else key
        return xml.array(processDict(key, value[0]), alias)
    else:
        return xml.array(xml.dictionary(key, []))

def processElse(key, _):
    return xml.string('.', attribute=key, required=False)

def traverseDict(thisDict, processDict, processList, processElse):
    return (traverse(key, value, processDict, processList, processElse) for key, value in thisDict.items())

def traverseList(thisList, key, processDict, processList, processElse):
    return (traverse(key, value, processDict, processList, processElse) for value in thisList)

def traverse(key, value, processDict, processList, processElse):
    if processDict and isinstance(value, dict):
        return processDict(key, value)
    elif processList and isinstance(value, list):
        return processList(key, value)
    else:
        return processElse(key, value)

sock = Sock(app)

# Create singleton middleware instance
wsMiddleware = PlexWebSocketMiddleware()

async def checkRequestStatus(ratingKey, mediaType, mediaTypeNum, requestKey):
    try:
        # Generate a unique UUID for this refresh session
        uuid_str = str(uuid.uuid4())
        
        # Timeline notifications
        await wsMiddleware.injectNotification({
            "NotificationContainer": {
                "type": "timeline",
                "size": 1,
                "TimelineEntry": [
                    {
                        "identifier": "com.plexapp.plugins.library",
                        "sectionID": "1",
                        "itemID": requestKey,
                        "type": 1,
                        "title": "Big Buck Bunny (2008)",
                        "state": 3,
                        "metadataState": "queued",
                        "updatedAt": 1736128693
                    }
                ]
            }
        })

        # await asyncio.sleep(5)

        await wsMiddleware.injectNotification({
            "NotificationContainer": {
                "type": "timeline",
                "size": 1,
                "TimelineEntry": [
                    {
                        "identifier": "com.plexapp.plugins.library",
                        "sectionID": "1",
                        "itemID": requestKey,
                        "type": 1,
                        "title": "Big Buck Bunny (2008)",
                        "state": 5,
                        "updatedAt": 1736128693
                    }
                ]
            }
        })
                
    except Exception as e:
        print(f"Error checking request status: {e}")

@sock.route('/:/websockets/notifications')
def websocketEndpoint(ws):
    # Create event loop for this thread if it doesn't exist
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def handleWebsocket():
        try:
            # Add client and set up connection
            print('Starting websocket')
            await wsMiddleware.addClient(ws)
            
            while True:
                try:
                    # Use synchronous receive from Flask-Sock
                    message = ws.receive()
                    print('Receiving: ')
                    print(message)
                except:
                    break
        finally:
            # Clean up when connection ends
            print('Ending websocket')
            await wsMiddleware.removeClient(ws)
    
    # Run the async handler in the event loop
    loop.run_until_complete(handleWebsocket())

@app.route('/library/metadata/<mediaType>-<mediaTypeNum>-<ratingKey>', methods=['GET'])
@app.route('/library/metadata/<mediaType>-<mediaTypeNum>-<ratingKey>/<children>', methods=['GET'])
@app.route('/library/metadata/<mediaType>-<mediaTypeNum>-<ratingKey>-season-<season>', methods=['GET'])
@app.route('/library/metadata/<mediaType>-<mediaTypeNum>-<ratingKey>-season-<season>/<children>', methods=['GET'])
def libraryRequest(mediaType, mediaTypeNum, ratingKey, season=None, children=None):
    print('libraryRequest')
    token = request.headers.get('X-Plex-Token', None) or request.args.get('X-Plex-Token', None)
    originalRatingKey = ratingKey
    requestKey = f"{mediaType}-{mediaTypeNum}-{originalRatingKey}{f'-season-{season}' if mediaTypeNum == mediaTypeNums['season'] else ''}"

    try:
        if not mediaTypeNum or mediaTypeNum not in mediaTypeNums.values():
            print(f"Unknown mediaTypeNum: {mediaTypeNum}")
            discordError(f"Unknown mediaTypeNum: {mediaTypeNum}")

        if mediaTypeNum == mediaTypeNums['show'] or children:
            skipRequest = True

        headers = {
            **plexHeaders,
            'X-Plex-Token': token
        }

        guid = f"plex://{mediaType}/{ratingKey}"
        params = {**request.args}

        if mediaTypeNum != '0': 
            params['type'] = mediaTypeNum

        if mediaType == 'show':
            params['show.guid'] = guid
            if mediaTypeNum == mediaTypeNums['season']:
                params['season.index'] = season
        else:
            params['guid'] = guid

        allRequest = requests.get(f"{plex['serverHost']}/library/all", headers=headers, params=params)
        all = allRequest.json()

        mediaContainer = all['MediaContainer']

        # If you try and get a season that doesn't exist you'll get the show instead, if it does exist.
        if ('Metadata' in mediaContainer and 
            ((mediaContainer['Metadata'][0]['type'] == 'season' and mediaTypeNum == mediaTypeNums['season']) 
            or (mediaContainer['Metadata'][0]['type'] == 'movie' and mediaTypeNum == mediaTypeNums['movie'])
            or (mediaContainer['Metadata'][0]['type'] == 'show' and mediaTypeNum == mediaTypeNums['show']))):
            
            skipRequest = True

            if not children:    
                if mediaTypeNum == mediaTypeNums['season']:   
                    mediaContainer['Metadata'][0]['key'] = f"/library/metadata/{mediaType}-{mediaTypeNum}-{ratingKey}-season-{season}/children"

                response = jsonify(all)
                response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')

                return response

            if mediaTypeNum == mediaTypeNums['show']:
                return children(mediaContainer['Metadata'][0]['ratingKey'])

            metadataUrl = f"{plex['serverHost']}{mediaContainer['Metadata'][0]['key']}"
            metadataRequest = requests.get(metadataUrl, headers=headers, params=request.args)
            metadata = metadataRequest.json()

            response = jsonify(metadata)
            response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
            return response
        else:
            metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
            args = {k: v for k, v in request.args.items() if k != 'X-Plex-Token'}

            if not children and mediaTypeNum == mediaTypeNums['season']:
                metadataSeasonsRequest = requests.get(f"{plex['metadataHost']}library/metadata/{ratingKey}/children", headers=metadataHeaders, params=args)
                metadataSeasons = metadataSeasonsRequest.json()
                
                metadataSeason = next((s for s in metadataSeasons['MediaContainer']['Metadata'] if s['index'] == int(season)))
                ratingKey = metadataSeason['ratingKey']
            
            urlSuffix = "/children" if children else ""
            metadataMetadataRequest = requests.get(f"{plex['metadataHost']}library/metadata/{ratingKey}{urlSuffix}", headers=metadataHeaders, params=args)
            metadata = metadataMetadataRequest.json()
            
            if 'MediaContainer' in metadata and 'Metadata' in metadata['MediaContainer']:
                if children:
                    if mediaTypeNum == mediaTypeNums['season']:
                            metadata['MediaContainer']['Metadata'] = []
                    elif mediaTypeNum == mediaTypeNums['show']:
                        seasons = metadata['MediaContainer']['Metadata']
                        metadata['MediaContainer']['Metadata'] = []
                        metadata['MediaContainer'] = addRequestableSeasons(metadata['MediaContainer'], seasons, originalRatingKey)
                else:
                    item = metadata['MediaContainer']['Metadata'][0]

                    parentTitle = item.get('parentTitle', '')
                    title = item.get('title', '')
                    title = f"{parentTitle}: {title}" if parentTitle else title

                    if mediaTypeNum == mediaTypeNums['show']:
                        item['title'] = f"Request - {title}"
                    else:
                        item['title'] = f"{title} - Requesting..."

                    if mediaTypeNum == mediaTypeNums['season']:
                        item['key'] = f"/library/metadata/{mediaType}-{mediaTypeNum}-{originalRatingKey}-season-{season}/children"
                    else:
                        item['key'] = f"/library/metadata/{mediaType}-{mediaTypeNum}-{originalRatingKey}/children" 
            
            response = jsonify(metadata)
            response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
            return response

    except:
        e = traceback.format_exc()

        print(f"Error in /library/request")
        print(e)

        discordError(f"Error in /library/request", e)
        return 'Server Error', 500
    finally:
        if not locals().get('skipRequest', False):
            title = locals().get('title', 'Untitled')
            requestMedia(token, originalRatingKey, mediaType, season, title, mediaTypeNum, requestKey)
 

def requestMedia(token, ratingKey, mediaType, season, title, mediaTypeNum, requestKey):
    print('requestMedia')

    try:
        cacheKey = ratingKey if mediaType == 'movie' else f"{ratingKey}_{season}"
        recentlyRequested = cache.get(cacheKey) or []
        if token not in recentlyRequested:
            user = getUserForPlexServerToken(token)
            metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
            
            requestItem(user, ratingKey, datetime.now().timestamp(), metadataHeaders, getSeason=lambda: [int(season)])

            recentlyRequested.append(token)
            cache.set(cacheKey, recentlyRequested)

            # loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(loop)
            
            # Start status checking in background
            async def runStatusCheck():
                attempts = 0
                while attempts < 30:  # Run for 5 minutes (300 seconds)
                    attempts += 1
                    await asyncio.sleep(10)
                    await checkRequestStatus(ratingKey, mediaType, mediaTypeNum, requestKey)
                
            # Run the async handler in the event loop
            # loop.run_until_complete(runStatusCheck())

            # await runStatusCheck()
            Thread(target=lambda: asyncio.run(runStatusCheck())).start()
            
            print(f"{title} - Requested by {user['displayName']} via Plex Request")
            discordUpdate(f"{title} - Requested by {user['displayName']} via Plex Request", f"User Id: {user['id']}, Media Type: {mediaType}, {f'Season: {season},' if season else ''} Rating Key: {ratingKey}")
           
    except:
        e = traceback.format_exc()
        print(f"Error in request")
        print(e)

        discordError(f"Error in request", e)

@app.route('/library/all', methods=['GET'])
def all():
    try:
        headers = {
            **request.headers,
            'Accept': 'application/json',
        }

        allRequest = requests.get(f"{plex['serverHost']}/library/all", headers=headers, params=request.args)

        if allRequest.status_code != 200:
            return allRequest.text, allRequest.status_code

        all = allRequest.json()

        mediaContainer = all['MediaContainer']

        if not 'Metadata' in mediaContainer:
            fullGuid = (request.args.get('guid', None) or request.args.get('show.guid'))
            guidMatch = re.match('plex:\/\/(.+?)\/(.+?)(?:\/|$)', fullGuid)

            mediaType, guid = guidMatch.group(1, 2)
            season = request.args.get('season.index')
            mediaTypeNum = request.args.get('type', mediaTypeNums['movie'] if mediaType == 'movie' else mediaTypeNums['season'] if season else mediaTypeNums['show'])

            if mediaType != 'episode' and (mediaTypeNum != mediaTypeNums['season'] or season != '0'):
                metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
                args = {k: v for k, v in request.args.items() if k != 'X-Plex-Token'}

                urlSuffix = "/children" if mediaTypeNum == mediaTypeNums['season'] else ""
                metadataAllRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}{urlSuffix}", headers=metadataHeaders, params=args)
                if metadataAllRequest.status_code == 200:
                    libraryId = plex['serverMovieLibraryId'] if mediaType == 'movie' else plex['serverTvShowLibraryId']

                    additionalMetadata = metadataAllRequest.json()['MediaContainer']['Metadata'][0]
                    if mediaTypeNum == mediaTypeNums['season'] or mediaTypeNum == mediaTypeNums['episode']:
                        additionalMetadata['key'] = f"/library/metadata/{mediaType}-{mediaTypeNum}-{guid}-season-{season}"
                        additionalMetadata['ratingKey'] = f"{mediaType}-{mediaTypeNum}-{guid}-season-{season}"
                    else:
                        additionalMetadata['key'] = f"/library/metadata/{mediaType}-{mediaTypeNum}-{guid}"
                        additionalMetadata['ratingKey'] = f"{mediaType}-{mediaTypeNum}-{guid}"

                    additionalMetadata['librarySectionTitle'] = "Request Season :" if mediaTypeNum == mediaTypeNums['episode'] else "Request :"
                    additionalMetadata['librarySectionID'] = libraryId
                    additionalMetadata['librarySectionKey'] = f"/library/sections/{libraryId}"
                    additionalMetadata['Media'] = [{
                        "videoResolution": "Request Season :" if mediaTypeNum == mediaTypeNums['episode'] else "Request :"
                    }]
                    additionalMetadata['childCount'] = 0
                    mediaContainer['size'] = 1
                    mediaContainer['Metadata'] = [additionalMetadata]

        if request.accept_mimetypes.best_match(['application/xml', 'application/json']) == 'application/json':
            response = jsonify(all)
            cors = allRequest.headers.get('Access-Control-Allow-Origin', None)
            if cors:
                response.headers.add('Access-Control-Allow-Origin', cors)
        else:
            processor = processDict('MediaContainer', mediaContainer)
            xmlString = xml.serialize_to_string(processor, mediaContainer, '    ')
            response = Response(xmlString, mimetype='application/xml')

            if 'fullGuid' in locals():
                print('Request in xml')

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/all")
        print(e)

        discordError(f"Error in /library/all", e)
        return 'Server Error', 500

@app.route('/library/metadata/<metadataRatingKey:id>/children', methods=['GET'])
def metadataChildren(id):
    metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
    args = {k: v for k, v in request.args.items() if k != 'X-Plex-Token'}

    metadataChildrenRequest = requests.get(f"{plex['metadataHost']}library/metadata/{id}/children", headers=metadataHeaders, params=args)
    if metadataChildrenRequest.status_code != 200:
            return metadataChildrenRequest.text, metadataChildrenRequest.status_code

    children = metadataChildrenRequest.json()
    mediaContainer = children['MediaContainer']
    
    if request.accept_mimetypes.best_match(['application/xml', 'application/json']) == 'application/json':
        response = jsonify(children)
        cors = metadataChildrenRequest.headers.get('Access-Control-Allow-Origin', None)
        if cors:
            response.headers.add('Access-Control-Allow-Origin', cors)
    else:
        processor = processDict('MediaContainer', mediaContainer)
        xmlString = xml.serialize_to_string(processor, mediaContainer, '    ')
        response = Response(xmlString, mimetype='application/xml')

        if 'fullGuid' in locals():
            print('Request in xml')

    return response

@app.route('/library/metadata/<id>/children', methods=['GET'])
def children(id):
    try:
        headers = {
            **request.headers,
            'Accept': 'application/json',
        }

        childrenRequest = requests.get(f"{plex['serverHost']}/library/metadata/{id}/children", headers=headers, params=request.args)

        if childrenRequest.status_code != 200:
            return childrenRequest.text, childrenRequest.status_code

        children = childrenRequest.json()

        mediaContainer = children['MediaContainer']

        if 'viewGroup' in mediaContainer and mediaContainer['viewGroup'] == "season" and 'Metadata' in mediaContainer and mediaContainer['Metadata']:
            fullGuid = mediaContainer['Metadata'][0]['parentGuid']
            guidMatch = re.match('plex:\/\/(.+?)\/(.+?)(?:\/|$)', fullGuid)

            _, guid = guidMatch.group(1, 2)

            metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
            args = {k: v for k, v in request.args.items() if k != 'X-Plex-Token'}

            metadataChildrenRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}/children", headers=metadataHeaders, params=args)
            if metadataChildrenRequest.status_code == 200:
                seasons = metadataChildrenRequest.json().get('MediaContainer', {}).get('Metadata', [])
                mediaContainer = addRequestableSeasons(mediaContainer, seasons, guid)

        if request.accept_mimetypes.best_match(['application/xml', 'application/json']) == 'application/json':
            response = jsonify(children)
            cors = childrenRequest.headers.get('Access-Control-Allow-Origin', None)
            if cors:
                response.headers.add('Access-Control-Allow-Origin', cors)
        else:
            processor = processDict('MediaContainer', mediaContainer)
            xmlString = xml.serialize_to_string(processor, mediaContainer, '    ')
            response = Response(xmlString, mimetype='application/xml')

            if 'fullGuid' in locals():
                print('Request in xml')

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/metadata/{id}/children")
        print(e)

        discordError(f"Error in /library/metadata/{id}/children", e)
        return 'Server Error', 500

def addRequestableSeasons(mediaContainer, seasons, ratingKey):
    allSeasons = [item for item in seasons if item['index'] != 0]
    metadata = mediaContainer.get('Metadata', [])
    existingMetadataIndices = {item['index']: item for item in metadata} 
    
    for item in allSeasons:
        if item['index'] not in existingMetadataIndices:
            item['title'] = f"Request - {item.get('title', '')}" 
            item['key'] = f"/library/metadata/show-{mediaTypeNums['season']}-{ratingKey}-season-{item['index']}"
            item['ratingKey'] = f"show-{mediaTypeNums['season']}-{ratingKey}-season-{item['index']}"
            item.pop('Guid', None)
            item.pop('Image', None)
            item.pop('Role', None)
            item.pop('banner', None)
            item.pop('contentRating', None)
            item.pop('hasGenericTitle', None)
            item.pop('originallyAvailableAt', None)
            item.pop('parentArt', None)
            item.pop('parentType', None)
            item.pop('publicPagesURL', None)
            item.pop('userState', None)
            item.pop('year', None)
            item.pop('parentKey', None)
            metadata.append(item)
    metadata.sort(key=lambda x: x['index'])
    mediaContainer['size'] = len(metadata)
    mediaContainer['totalSize'] = len(metadata)

    return mediaContainer

if __name__ == '__main__':
    app.run('127.0.0.1', 12599, debug=True)