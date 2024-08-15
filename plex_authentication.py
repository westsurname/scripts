import requests
import json
import urllib.parse
from flask import Flask, jsonify, redirect, url_for, request
from shared.shared import watchlist, plexHeaders, tokensFilename
from shared.overseerr import getUserForPlexToken
from shared.plex import getServerToken
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
app.url_map.strict_slashes = False


@app.route('/', methods=['GET'])
def setup():
    pinRequest = requests.post('https://plex.tv/api/v2/pins', headers=plexHeaders, json={'strong': True, 'X-Plex-Version': watchlist['plexVersion'], 'X-Plex-Product': watchlist['plexProduct'], 'X-Plex-Client-Identifier': watchlist['plexClientIdentifier']})
    pin = pinRequest.json()

    return redirect('https://app.plex.tv/auth#?' + urllib.parse.urlencode({
        'clientID': watchlist['plexClientIdentifier'],
        'code': pin['code'],
        'forwardUrl': url_for('setupComplete', pin=pin['id'], _external=True),
        'context[device][product]': watchlist['plexProduct']
    }))

@app.route('/complete/<pin>', methods=['GET'])
def setupComplete(pin):
    pinRequest = requests.get(f"https://plex.tv/api/v2/pins/{pin}", headers=plexHeaders, json={'X-Plex-Client-Identifier': watchlist['plexClientIdentifier']})

    if pinRequest.status_code == 200:
        authToken = pinRequest.json()['authToken']

        if authToken:
            return handleToken(authToken)

    return jsonify('There was an error, please try again.')

@app.route('/token', methods=['POST'])
def receiveToken():
    token = request.json.get('token')
    if token:
        return handleToken(token)
    else:
        return createResponse({'error': 'No token provided'}, 400)

def handleToken(token):
    user = getUserForPlexToken(token)
    serverToken = getServerToken(token)
    userId = user['id']

    updateTokensFile(userId, token, serverToken)

    return createResponse({'message': 'Token received and stored successfully'}, 201)

def updateTokensFile(userId, token, serverToken):
    with open(tokensFilename, 'r+') as tokensFile:
        tokens = json.load(tokensFile)
        tokenEntry = tokens.get(userId, {'etag': ''})
        tokenEntry['token'] = token
        tokenEntry['serverToken'] = serverToken
        tokens[userId] = tokenEntry
        tokensFile.seek(0)
        json.dump(tokens, tokensFile)
        tokensFile.truncate()

def createResponse(data, statusCode):
    response = jsonify(data), statusCode
    return response

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/auth': app.wsgi_app})

if __name__ == '__main__':
    app.run('127.0.0.1', 12598)