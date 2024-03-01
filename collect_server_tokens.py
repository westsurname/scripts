import json
from shared.shared import tokensFilename
from shared.plex import getServerToken

with open(tokensFilename, 'r+') as tokensFile:
    tokens = json.load(tokensFile)
    for id, token in tokens.items():
        token['serverToken'] = getServerToken(token['token'])
    tokensFile.seek(0)
    json.dump(tokens, tokensFile)
    tokensFile.truncate()