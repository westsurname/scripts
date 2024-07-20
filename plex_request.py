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
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ... (previous code remains unchanged)

@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>', methods=['GET'])
@app.route('/library/request/<mediaType>/<mediaTypeNum>/<ratingKey>/season/<season>', methods=['GET'])
def requestRatingKey(mediaType, mediaTypeNum, ratingKey, season=None):
    logger.debug(f"Entering requestRatingKey function with parameters: mediaType={mediaType}, mediaTypeNum={mediaTypeNum}, ratingKey={ratingKey}, season={season}")
    
    try:
        token = request.headers.get('X-Plex-Token', None) or request.args.get('X-Plex-Token', None)
        logger.debug(f"Token received: {'Yes' if token else 'No'}")
        
        headers = {
            **plexHeaders,
            'X-Plex-Token': token,
            'Accept': 'application/json'
        }
        logger.debug(f"Headers: {json.dumps(headers, indent=2)}")
        
        recentlyRequested = cache.get(ratingKey) or []
        logger.debug(f"Recently requested for ratingKey {ratingKey}: {recentlyRequested}")
        
        if token not in recentlyRequested:
            logger.info(f"{ratingKey} Not in recentRequests. Requesting item...")
            
            user = getUserForPlexServerToken(token)
            logger.debug(f"User for token: {user}")
            
            requestItem(user, ratingKey, datetime.now().timestamp(), headers, getSeason=lambda: [int(season)] if season else None)
            logger.info(f"Item requested for user {user}")

            recentlyRequested.append(token)
            cache.set(ratingKey, recentlyRequested)
            discordUpdate('Request made via new system!', ratingKey)
            logger.info(f"Request recorded and Discord updated for ratingKey {ratingKey}")

        params = {'includeChildren': 1}
        guid = f"plex://{mediaType}/{ratingKey}"
        logger.debug(f"GUID constructed: {guid}")

        # Prioritize the /library/all endpoint
        endpoints = [
            f"/library/all",
            f"/library/metadata/{ratingKey}",
            f"/library/sections/{mediaTypeNum}/all"
        ]
        logger.debug(f"Endpoints to try: {endpoints}")

        all_response = None
        for endpoint in endpoints:
            try:
                if endpoint == "/library/all":
                    params['guid'] = guid
                elif mediaType == 'show' and season is not None:
                    params['guid'] = guid
                    params['season.index'] = season

                encoded_params = urllib.parse.urlencode(params)
                url = f"{plex['serverHost']}{endpoint}?{encoded_params}"
                logger.info(f"Attempting request to URL: {url}")
                
                allRequest = requests.get(url, headers=headers, timeout=10)
                
                logger.debug(f"Request URL: {allRequest.url}")
                logger.debug(f"Request Headers: {json.dumps(dict(allRequest.request.headers), indent=2)}")
                logger.debug(f"Response Status Code: {allRequest.status_code}")
                logger.debug(f"Response Headers: {json.dumps(dict(allRequest.headers), indent=2)}")
                logger.debug(f"Response Content (first 500 chars): {allRequest.text[:500]}")

                if allRequest.status_code == 200:
                    all_response = allRequest
                    logger.info(f"Successful response from endpoint: {endpoint}")
                    break
                else:
                    logger.warning(f"Request to {endpoint} failed with status code {allRequest.status_code}")
            except requests.RequestException as e:
                logger.error(f"Request to {endpoint} failed: {str(e)}")

        if all_response is None:
            error_message = {'error': 'Unable to fetch metadata from any endpoint', 'tried_endpoints': endpoints}
            logger.error(f"All endpoints failed. Error message: {json.dumps(error_message, indent=2)}")
            return jsonify(error_message), 404

        try:
            all = all_response.json()
            logger.debug(f"JSON response received: {json.dumps(all, indent=2)[:1000]}...")  # First 1000 chars
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {all_response.text}")
            return jsonify({'error': 'Invalid JSON response from server'}), 500

        mediaContainer = all.get('MediaContainer', {})
        logger.debug(f"MediaContainer: {json.dumps(mediaContainer, indent=2)[:1000]}...")  # First 1000 chars

        if 'Metadata' in mediaContainer and mediaContainer['Metadata']:
            metadata = mediaContainer['Metadata'][0]
            logger.debug(f"Metadata found: {json.dumps(metadata, indent=2)[:1000]}...")  # First 1000 chars
            
            if mediaType == 'show' and season is not None:
                seasons = metadata.get('Children', {}).get('Metadata', [])
                season_metadata = next((s for s in seasons if s.get('index') == int(season)), None)
                
                if season_metadata:
                    metadata = season_metadata
                    logger.debug(f"Season metadata found: {json.dumps(metadata, indent=2)[:1000]}...")  # First 1000 chars
                else:
                    logger.warning(f"Season {season} not found in metadata")
                    return jsonify({'error': f'Season {season} not found'}), 404

            response = jsonify(metadata)
            response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
            logger.info("Successful response generated")
            return response

        logger.warning("Metadata not found in MediaContainer")
        response = jsonify({'error': 'Metadata not found', 'mediaContainer': mediaContainer})
        response.headers.add('Access-Control-Allow-Origin', 'https://app.plex.tv')
        return response, 404

    except Exception as e:
        logger.error(f"Unexpected error in /library/request: {str(e)}")
        logger.error(traceback.format_exc())

        discordError(f"Error in /library/request", str(e))

        return jsonify({'error': 'Server Error', 'details': str(e)}), 500

# ... (rest of the code remains unchanged)
