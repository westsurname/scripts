from datetime import datetime
import os
import traceback
import re
import time
import requests
import json
import urllib.parse
import declxml as xml
from flask import Flask, jsonify, request, Response
from flask_caching import Cache
from shared.discord import discordError, discordUpdate
from shared.shared import plex, plexHeaders, pathToScript
from shared.overseerr import requestItem, getUserForPlexServerToken

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
app.url_map.strict_slashes = False

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
        alias = None
        if key == 'Metadata':
            alias = key
            key = 'Video' # 'Directory'?
        
        return xml.array(processDict(key, value[0]), alias)
    else:
        # Will this break?
        return xml.array(xml.dictionary(key, []))

def processElse(key, _):
    return xml.string('.', attribute=key, required=False)

def traverseDict(thisDict, processDict, processList, processElse):
    return (traverse(key, value, processDict,  processList, processElse) for key, value in thisDict.items())
            
def traverseList(thisList, key, processDict, processList, processElse):
    return (traverse(key, value, processDict, processList, processElse) for value in thisList)

def traverse(key, value, processDict, processList, processElse):
    if processDict and isinstance(value, dict):
        return processDict(key, value)
    elif processList and isinstance(value, list):
        return processList(key, value)
    else: 
        return processElse(key, value)


# TODO: Make routes not / sensitive
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>', methods=['GET'])
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>/season/<season>', methods=['GET'])
def requestRatingKey(mediaType, mediaTypeNum, ratingKey, season=None):
    try:
        token = request.headers.get('X-Plex-Token', None) or request.args.get('X-Plex-Token', None)
        # print(token)
        headers = {
            **plexHeaders,
            'X-Plex-Token': token
        }
        # global recentRequests
        # print(recentRequests)
        # recentRequests = { ratingKey:time for (ratingKey, time) in recentRequests.items() if datetime.now() - datetime.fromtimestamp(time) < timedelta(hours=1) }
        # print(recentRequests)
        recentlyRequested = cache.get(ratingKey) or []
        print(recentlyRequested)
        # if not ratingKey in recentRequests:
        if not token in recentlyRequested:
            print(ratingKey, 'Not in recentRequests')
            
            user = getUserForPlexServerToken(token)
            metadataHeaders = {
                **plexHeaders,
                'X-Plex-Token': plex['serverApiKey']
            }
            requestItem(user, ratingKey, datetime.now().timestamp(), metadataHeaders, getSeason=lambda: [int(season)])

            recentlyRequested.append(token)
            cache.set(ratingKey, recentlyRequested)
            discordUpdate('Request made via new system!', ratingKey)

        params = {'type': mediaTypeNum} if mediaTypeNum != '0' else {}
        guid = f"plex://{mediaType}/{ratingKey}"

        if mediaType == 'show' and season is not None:
            params['show.guid'] = guid
            params['season.index'] = season
        else:
            params['guid'] = guid

        for _ in range(15):
            allRequest = requests.get(f"{plex['serverHost']}/library/all", headers=headers, params=params)
            # print(allRequest.url)
            all = allRequest.json()

            mediaContainer = all['MediaContainer']

            if 'Metadata' in mediaContainer:
                metadataRequest = requests.get(f"{plex['serverHost']}{mediaContainer['Metadata'][0]['key']}?includeConcerts=1&includeExtras=1&includeOnDeck=1&includePopularLeaves=1&includePreferences=1&includeReviews=1&includeChapters=1&includeStations=1&includeExternalMedia=1&asyncAugmentMetadata=1&asyncCheckFiles=1&asyncRefreshAnalysis=1&asyncRefreshLocalMediaAgent=1", headers=headers)
                # print(metadataRequest)
                # print(metadataRequest.url)
                metadata = metadataRequest.json()

                response = jsonify(metadata)
                # print(response.json)
                response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
                return response

            time.sleep(1)

        # attemptNum = int(request.args.get('attemtnum', '1'))

        # if not attemptNum or attemptNum <= 3:
        #     query = {
        #         **request.args,
        #         'attemptnum': attemptNum + 1
        #     }
        #     queryString = urllib.parse.urlencode(query)
        #     response = redirect(url_for("requestRatingKey", mediaType=mediaType, mediaTypeNum=mediaTypeNum, ratingKey=ratingKey, season=season) + '?' + queryString)  #request.host_url base_ur.replace(request.base_url, '')) #url_for("requestRatingKey", mediaType=mediaType, mediaTypeNum=mediaTypeNum, ratingKey=ratingKey, season=season))
        #     # for key, value in request.headers.items():
        #     #     response.headers[key] = value 
        #     return response
        
        # response = jsonify(json.loads(blankMediaContainer))
        response = Response('', status=204)
        response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/request")
        print(e)

        discordError(f"Error in /library/request", e)

        return 'Server Error', 500
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

        print(allRequest)
        print(request.headers.get('Accept'))
        all = allRequest.json()

        mediaContainer = all['MediaContainer']

        if not 'Metadata' in mediaContainer:
            fullGuid = (request.args.get('guid', None) or request.args.get('show.guid'))
            guidMatch = re.match('plex:\/\/(.+?)\/(.+?)(?:\/|$)', fullGuid)

            mediaType, guid = guidMatch.group(1, 2)
            mediaTypeNum = request.args.get('type', '0')
            season = request.args.get('season.index', '1' if mediaType == 'show' else None)

            if mediaType != 'episode':
                token = headers.get('X-Plex-Token', request.args.get('X-Plex-Token'))
                user = getUserForPlexServerToken(token)
                metadataHeaders = {
                    **plexHeaders,
                    'X-Plex-Token': plex['serverApiKey']
                }

                args = dict(request.args)
                if 'X-Plex-Token' in args:
                    del args['X-Plex-Token']

                metadataAllRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}", headers=metadataHeaders, params=args)
                # print(f"{plex['metadataHost']}library/metadata/{guid}")
                # print(metadataHeaders)
                # print(args)
                print(metadataAllRequest)
                # print(metadataAllRequest.text)
                if metadataAllRequest.status_code == 200:
                    additionalMetadata = metadataAllRequest.json()['MediaContainer']['Metadata'][0]
                    # if additionalMetadata:
                    #     mediaContainer['Metadata'] = additionalMetadata
                    additionalMetadata['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{guid}{f'/season/{season}' if season is not None else ''}"
                    # additionalMetadata['guid'] = fullGuid
                    additionalMetadata['ratingKey'] = "12065"
                    additionalMetadata['librarySectionTitle'] = "Request (WIP)"
                    additionalMetadata['librarySectionID'] = 1
                    additionalMetadata['librarySectionKey'] = "/library/sections/1"
                    additionalMetadata['Media'] = [{
                        "videoResolution": "Request (WIP)"
                    }]
                    mediaContainer['size'] = 1
                    mediaContainer['Metadata'] = [additionalMetadata]

        if request.accept_mimetypes.best_match(['application/xml', 'application/json']) == 'application/json':
            print('accepts json')
            response = jsonify(all)
            cors = allRequest.headers.get('Access-Control-Allow-Origin', None)
            if cors:
                # Add others if required
                response.headers.add('Access-Control-Allow-Origin', cors)
            # response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
        else:
            print('doesn\'t accept json')

            processor = processDict('MediaContainer', mediaContainer)
            xmlString = xml.serialize_to_string(processor, mediaContainer, '    ')
            response = Response(xmlString, mimetype='application/xml')

            if 'fullGuid' in locals():
                print('Request in xml')
                print(xmlString)

                discordError('Request in xml', xmlString)

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/all")
        print(e)

        discordError(f"Error in /library/all", e)
                
        return 'Server Error', 500

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

        print(childrenRequest)
        print(request.headers.get('Accept'))
        children = childrenRequest.json()

        mediaContainer = children['MediaContainer']

        if 'viewGroup' in mediaContainer and mediaContainer['viewGroup'] == "season" and 'Metadata' in mediaContainer and mediaContainer['Metadata']:
            fullGuid = mediaContainer['Metadata'][0]['parentGuid']
            guidMatch = re.match('plex:\/\/(.+?)\/(.+?)(?:\/|$)', fullGuid)

            mediaType, guid = guidMatch.group(1, 2)
            mediaTypeNum = 0

            existing_seasons = {int(item['index']) for item in mediaContainer.get('Metadata', []) if item['type'] == 'season'}
            highest_season = max(existing_seasons) if existing_seasons else 0

            token = headers.get('X-Plex-Token', request.args.get('X-Plex-Token'))
            user = getUserForPlexServerToken(token)
            metadataHeaders = {
                **plexHeaders,
                'X-Plex-Token': plex['serverApiKey']
            }

            args = dict(request.args)
            if 'X-Plex-Token' in args:
                del args['X-Plex-Token']

            metadataChildrenRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}/children", headers=metadataHeaders, params=args)
            print(metadataChildrenRequest)
            # print(metadataChildrenRequest.text)
            if metadataChildrenRequest.status_code == 200:
                additionalMetadata = metadataChildrenRequest.json().get('MediaContainer', {}).get('Metadata', [])
                metadata = mediaContainer['Metadata']
                existingMetadataIndices = {item['index']: item for item in metadata} 
                # Combine additional metadata with existing, preferring existing entries
                for item in additionalMetadata:
                    if item['index'] not in existingMetadataIndices:
                        item['title'] = f"Request {item.get('title', '')}" 
                        item['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{guid}/season/{item['index']}"
                        item['ratingKey'] = "12065"
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
                        # thumb_url = f"https://textoverimage.moesif.com/image?image_url={item['thumb']}&overlay_color=ffffffaa&text=Request&text_color=282828ff&text_size=128&y_align=middle&x_align=center"
                        # item['thumb'] = thumb_url
                        metadata.append(item)
                metadata.sort(key=lambda x: x['index'])
                mediaContainer['size'] = len(metadata)
                mediaContainer['totalSize'] = len(metadata)

        if request.accept_mimetypes.best_match(['application/xml', 'application/json']) == 'application/json':
            print('accepts json')
            response = jsonify(children)
            cors = childrenRequest.headers.get('Access-Control-Allow-Origin', None)
            if cors:
                response.headers.add('Access-Control-Allow-Origin', cors)
        else:
            print('doesn\'t accept json')

            processor = processDict('MediaContainer', mediaContainer)
            xmlString = xml.serialize_to_string(processor, mediaContainer, '    ')
            response = Response(xmlString, mimetype='application/xml')

            if 'fullGuid' in locals():
                print('Request in xml')
                print(xmlString)

                discordError('Request in xml', xmlString)

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/metadata/{id}/children")
        print(e)

        discordError(f"Error in /library/metadata/{id}/children", e)
                
        return 'Server Error', 500    
    
if __name__ == '__main__':
    app.run('127.0.0.1', 12599, debug=True)