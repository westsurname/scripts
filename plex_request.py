from datetime import datetime
import os
import traceback
import re
import requests
import json
import declxml as xml
from flask import Flask, jsonify, request, Response
from flask_caching import Cache
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

# Instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
app.url_map.strict_slashes = False
app.url_map.converters['metadataRatingKey'] = MetadataRatingKeyConverter

# Setup caching
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

@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>', methods=['GET'])
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>/<children>', methods=['GET'])
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>/season/<season>', methods=['GET'])
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>/season/<season>/<children>', methods=['GET'])
def requestRatingKey(mediaType, mediaTypeNum, ratingKey, season=None, children=None):
    try:
        print(f"Processing request for {mediaType} with rating key {ratingKey}")
        token = request.headers.get('X-Plex-Token') or request.args.get('X-Plex-Token')
        headers = {**plexHeaders, 'X-Plex-Token': token}

        if mediaType == 'movie' or (mediaType == 'show' and season is not None):
            cacheKey = ratingKey if mediaType == 'movie' else f"{ratingKey}_{season}"
            recentlyRequested = cache.get(cacheKey) or []
            
            if token not in recentlyRequested:
                user = getUserForPlexServerToken(token)
                metadataHeaders = {**plexHeaders, 'X-Plex-Token': plex['serverApiKey']}
                requestItem(user, ratingKey, datetime.now().timestamp(), metadataHeaders, getSeason=lambda: [int(season)])

                recentlyRequested.append(token)
                cache.set(cacheKey, recentlyRequested)
                discordUpdate('Request made via new system!', cacheKey)

        guid = f"plex://{mediaType}/{ratingKey}"
        params = {**request.args}

        if mediaTypeNum != '0':
            params['type'] = mediaTypeNum

        if mediaType == 'show' and season is not None:
            params['show.guid'] = guid
            params['season.index'] = season
        else:
            params['guid'] = guid

        allRequest = requests.get(f"{plex['serverHost']}/library/all", headers=headers, params=params)
        all = allRequest.json()

        mediaContainer = all['MediaContainer']
        if 'Metadata' in mediaContainer and (mediaContainer['Metadata'][0]['type'] == 'season' or mediaContainer['Metadata'][0]['type'] == 'movie'):
            if not children and mediaType == 'show':   
                mediaContainer['Metadata'][0]['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{ratingKey}/season/{season}/children"

                response = jsonify(all)
                response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')

                return response

            metadataUrl = f"{plex['serverHost']}{mediaContainer['Metadata'][0]['key']}"
            metadataRequest = requests.get(metadataUrl, headers=headers, params=request.args)
            metadata = metadataRequest.json()

            response = jsonify(metadata)
            response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
            return response
        else:
            metadataHeaders = {
                **plexHeaders,
                'X-Plex-Token': plex['serverApiKey']
            }

            args = dict(request.args)
            if 'X-Plex-Token' in args:
                del args['X-Plex-Token']

            if not children and mediaType == 'show' and season is not None:
                metadataSeasonsRequest = requests.get(f"{plex['metadataHost']}library/metadata/{ratingKey}/children", headers=metadataHeaders, params=args)
                metadataSeasons = metadataSeasonsRequest.json()
                
                metadataSeason = next((s for s in metadataSeasons['MediaContainer']['Metadata'] if s['index'] == int(season)))
                ratingKey = metadataSeason['ratingKey']
            
            urlSuffix = "/children" if children else ""
            metadataMetadataRequest = requests.get(f"{plex['metadataHost']}library/metadata/{ratingKey}{urlSuffix}", headers=metadataHeaders, params=args)
            metadata = metadataMetadataRequest.json()
            
            if children and mediaType == 'show' and season is not None:
                if 'MediaContainer' in metadata and 'Metadata' in metadata['MediaContainer']:
                    metadata['MediaContainer']['Metadata'] = []

            if not children:
                if mediaType == 'show' and season is not None:
                    metadata['MediaContainer']['Metadata'][0]['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{ratingKey}/season/{season}/children"
                else:
                    metadata['MediaContainer']['Metadata'][0]['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{ratingKey}/children" 

            response = jsonify(metadata)
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
        print("Processing /library/all request")
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
            mediaTypeNum = request.args.get('type', '0')
            season = request.args.get('season.index', '1' if mediaTypeNum == mediaTypeNums['season'] else None)

            if mediaType != 'episode':
                metadataHeaders = {
                    **plexHeaders,
                    'X-Plex-Token': plex['serverApiKey']
                }

                args = dict(request.args)
                if 'X-Plex-Token' in args:
                    del args['X-Plex-Token']

                urlSuffix = "/children" if mediaTypeNum == mediaTypeNums['season'] else ""
                metadataAllRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}{urlSuffix}", headers=metadataHeaders, params=args)
                if metadataAllRequest.status_code == 200:
                    additionalMetadata = metadataAllRequest.json()['MediaContainer']['Metadata'][0]

                    if mediaTypeNum == mediaTypeNums['season'] or mediaTypeNum == mediaTypeNums['episode']:
                        additionalMetadata['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{guid}/season/{season}"
                    else:
                        additionalMetadata['key'] = f"/library/request/{mediaType}/{mediaTypeNum}/{guid}"

                    additionalMetadata['ratingKey'] = "12065"
                    additionalMetadata['librarySectionTitle'] = "Request Season" if mediaTypeNum == mediaTypeNums['episode'] else "Request (WIP)"
                    additionalMetadata['librarySectionID'] = 1
                    additionalMetadata['librarySectionKey'] = "/library/sections/1"
                    additionalMetadata['Media'] = [{
                        "videoResolution": "Request Season" if mediaTypeNum == mediaTypeNums['episode'] else "Request (WIP)"
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
                discordError('Request in xml', xmlString)

        return response
    except:
        e = traceback.format_exc()

        print(f"Error in /library/all")
        print(e)

        discordError(f"Error in /library/all", e)
                
        return 'Server Error', 500

@app.route('/library/metadata/<metadataRatingKey:id>/children', methods=['GET'])
def metadataChildren(id):
    print(f"Processing metadata children request for id: {id}")
    metadataHeaders = {
        **plexHeaders,
        'X-Plex-Token': plex['serverApiKey']
    }

    args = dict(request.args)
    if 'X-Plex-Token' in args:
        del args['X-Plex-Token']

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
            discordError('Request in xml', xmlString)

    return response


@app.route('/library/metadata/<id>/children', methods=['GET'])
def children(id):
    try:
        print(f"Processing children request for id: {id}")
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

            mediaType, guid = guidMatch.group(1, 2)
            mediaTypeNum = mediaTypeNums['season']

            existing_seasons = {int(item['index']) for item in mediaContainer.get('Metadata', []) if item['type'] == 'season'}
            highest_season = max(existing_seasons) if existing_seasons else 0
            
            metadataHeaders = {
                **plexHeaders,
                'X-Plex-Token': plex['serverApiKey']
            }

            args = dict(request.args)
            if 'X-Plex-Token' in args:
                del args['X-Plex-Token']

            metadataChildrenRequest = requests.get(f"{plex['metadataHost']}library/metadata/{guid}/children", headers=metadataHeaders, params=args)
            if metadataChildrenRequest.status_code == 200:
                additionalMetadata = [item for item in metadataChildrenRequest.json().get('MediaContainer', {}).get('Metadata', []) if item['index'] != 0]
                metadata = mediaContainer['Metadata']
                existingMetadataIndices = {item['index']: item for item in metadata} 
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