import requests
import json
import urllib.parse
from flask import Flask, jsonify, redirect, url_for
from shared.shared import server, watchlist, plexHeaders, tokensFilename
from shared.overseerr import getUserForPlexToken
from shared.plex import getServerToken
from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

host = server['host']

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
# app.config['SERVER_NAME'] = f"{host}"


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
            user = getUserForPlexToken(authToken)
            serverToken = getServerToken(authToken)
            userId = user['id']

            with open(tokensFilename, 'r+') as tokensFile:
                tokens = json.load(tokensFile)
                token = tokens.get(userId, { 'etag': '' })
                token['token'] = authToken
                token['serverToken'] = serverToken

                if serverToken == authToken:
                    token['owner'] = True

                tokens[userId] = token
                tokensFile.seek(0)
                json.dump(tokens, tokensFile)
                tokensFile.truncate()

            return jsonify('Successfully authenticated!')

    return jsonify('There was an error, please try again.')

# app.wsgi_app = DispatcherMiddleware(run_simple, {'/plexAuthentication': app.wsgi_app})
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
if __name__ == '__main__':
    app.run('127.0.0.1', 12598)