import os
import re
from environs import Env

env = Env()
env.read_env()

default_pattern = r"<[a-z0-9_]+>"

def commonEnvParser(value, convert=None):
    if value is None:
        return None
    if re.match(default_pattern, value):
        return None
    return convert(value) if convert else value

@env.parser_for("integer")
def integerEnvParser(value):
    return commonEnvParser(value, int)

@env.parser_for("string")
def stringEnvParser(value):
    return commonEnvParser(value)

watchlist = {
    'plexProduct': env.string('WATCHLIST_PLEX_PRODUCT', default=None),
    'plexVersion': env.string('WATCHLIST_PLEX_VERSION', default=None),
    'plexClientIdentifier': env.string('WATCHLIST_PLEX_CLIENT_IDENTIFIER', default=None)
}

blackhole = {
    'baseWatchPath': env.string('BLACKHOLE_BASE_WATCH_PATH', default=None),
    'radarrPath': env.string('BLACKHOLE_RADARR_PATH', default=None),
    'sonarrPath': env.string('BLACKHOLE_SONARR_PATH', default=None),
    'failIfNotCached': env.bool('BLACKHOLE_FAIL_IF_NOT_CACHED', default=None),
    'rdMountRefreshSeconds': env.integer('BLACKHOLE_RD_MOUNT_REFRESH_SECONDS', default=None),
    'waitForTorrentTimeout': env.integer('BLACKHOLE_WAIT_FOR_TORRENT_TIMEOUT', default=None),
    'historyPageSize': env.integer('BLACKHOLE_HISTORY_PAGE_SIZE', default=None),
}

server = {
    'host': env.string('SERVER_DOMAIN', default=None)
}

plex = {
    'host': env.string('PLEX_HOST', default=None),
    'metadataHost': env.string('PLEX_METADATA_HOST', default=None),
    'serverHost': env.string('PLEX_SERVER_HOST', default=None),
    'serverMachineId': env.string('PLEX_SERVER_MACHINE_ID', default=None),
    'serverApiKey': env.string('PLEX_SERVER_API_KEY', default=None),
    'serverMovieLibraryId': env.integer('PLEX_SERVER_MOVIE_LIBRARY_ID', default=None),
    'serverTvShowLibraryId': env.integer('PLEX_SERVER_TV_SHOW_LIBRARY_ID', default=None),
    'serverPath': env.string('PLEX_SERVER_PATH', default=None),
}

overseerr = {
    'host': env.string('OVERSEERR_HOST', default=None),
    'apiKey': env.string('OVERSEERR_API_KEY', default=None)
}

sonarr = {
    'host': env.string('SONARR_HOST', default=None),
    'apiKey': env.string('SONARR_API_KEY', default=None)
}

radarr = {
    'host': env.string('RADARR_HOST', default=None),
    'apiKey': env.string('RADARR_API_KEY', default=None)
}

tautulli = {
    'host': env.string('TAUTULLI_HOST', default=None),
    'apiKey': env.string('TAUTULLI_API_KEY', default=None)
}

realdebrid = {
    'enabled': env.bool('REALDEBRID_ENABLED', default=True),
    'host': env.string('REALDEBRID_HOST', default=None),
    'apiKey': env.string('REALDEBRID_API_KEY', default=None),
    'mountTorrentsPath': env.string('REALDEBRID_MOUNT_TORRENTS_PATH', env.string('BLACKHOLE_RD_MOUNT_TORRENTS_PATH', default=None)),
    # Multiple accounts support
    'accounts': []
}

# Parse multiple Real-Debrid accounts
def parseRealdebridAccounts():
    accounts = []
    i = 1
    while True:
        # Support both numbered and non-numbered environment variables
        host_key = f'REALDEBRID_HOST_{i}' if i > 1 else 'REALDEBRID_HOST'
        api_key_key = f'REALDEBRID_API_KEY_{i}' if i > 1 else 'REALDEBRID_API_KEY'
        mount_path_key = f'REALDEBRID_MOUNT_TORRENTS_PATH_{i}' if i > 1 else 'REALDEBRID_MOUNT_TORRENTS_PATH'
        
        host = env.string(host_key, default=None)
        apiKey = env.string(api_key_key, default=None)
        mountPath = env.string(mount_path_key, env.string('BLACKHOLE_RD_MOUNT_TORRENTS_PATH', default=None) if i == 1 else None)
        
        if not host or not apiKey or not mountPath:
            if i == 1:
                # First account is required if RealDebrid is enabled
                print(f"Warning: Real-Debrid account {i} missing required environment variables")
                break
            else:
                # No more accounts found
                break
        
        # Validate that the mount path exists
        if not os.path.exists(mountPath):
            print(f"Warning: Real-Debrid account {i} mount path does not exist: {mountPath}")
        
        accounts.append({
            'id': i,
            'host': host,
            'apiKey': apiKey,
            'mountTorrentsPath': mountPath,
            'enabled': True,
            'rateLimited': False,
            'lastUsed': 0,
            'consecutiveFailures': 0,
            'lastHealthCheck': 0
        })
        
        print(f"Configured Real-Debrid account {i}: {host} -> {mountPath}")
        i += 1
    
    print(f"Total Real-Debrid accounts configured: {len(accounts)}")
    return accounts

# Initialize multiple accounts
if realdebrid['enabled']:
    realdebrid['accounts'] = parseRealdebridAccounts()
    # Keep backward compatibility
    if realdebrid['accounts']:
        realdebrid['host'] = realdebrid['accounts'][0]['host']
        realdebrid['apiKey'] = realdebrid['accounts'][0]['apiKey']
        realdebrid['mountTorrentsPath'] = realdebrid['accounts'][0]['mountTorrentsPath']

torbox = {
    'enabled': env.bool('TORBOX_ENABLED', default=None),
    'host': env.string('TORBOX_HOST', default=None),
    'apiKey': env.string('TORBOX_API_KEY', default=None),
    'mountTorrentsPath': env.string('TORBOX_MOUNT_TORRENTS_PATH', default=None)
}

trakt = {
    'apiKey': env.string('TRAKT_API_KEY', default=None)
}

discord = {
    'enabled': env.bool('DISCORD_ENABLED', default=None),
    'updateEnabled': env.bool('DISCORD_UPDATE_ENABLED', default=None),
    'webhookUrl': env.string('DISCORD_WEBHOOK_URL', default=None)
}

repair = {
    'repairInterval': env.string('REPAIR_REPAIR_INTERVAL', default=None),
    'runInterval': env.string('REPAIR_RUN_INTERVAL', default=None)
}

plexHeaders = {
    'Accept': 'application/json',
    'X-Plex-Product': watchlist['plexProduct'],
    'X-Plex-Version': watchlist['plexVersion'],
    'X-Plex-Client-Identifier': watchlist['plexClientIdentifier']
}

overseerrHeaders = {"X-Api-Key": f"{overseerr['apiKey']}"}

pathToScript = os.path.dirname(os.path.abspath(__file__))
tokensFilename = os.path.join(pathToScript, 'tokens.json')

# From Radarr Radarr/src/NzbDrone.Core/MediaFiles/MediaFileExtensions.cs
mediaExtensions = [
    ".m4v", 
    ".3gp", 
    ".nsv", 
    ".ty", 
    ".strm", 
    ".rm", 
    ".rmvb", 
    ".m3u", 
    ".ifo", 
    ".mov",        
    ".qt", 
    ".divx", 
    ".xvid", 
    ".bivx", 
    ".nrg", 
    ".pva", 
    ".wmv", 
    ".asf", 
    ".asx", 
    ".ogm", 
    ".ogv", 
    ".m2v", 
    ".avi", 
    ".bin", 
    ".dat", 
    ".dvr-ms", 
    ".mpg", 
    ".mpeg", 
    ".mp4", 
    ".avc", 
    ".vp3", 
    ".svq3", 
    ".nuv", 
    ".viv", 
    ".dv", 
    ".fli", 
    ".flv", 
    ".wpl", 
    ".img", 
    ".iso", 
    ".vob", 
    ".mkv", 
    ".mk3d", 
    ".ts", 
    ".wtv", 
    ".m2ts",
    ".webm" 
]

def intersperse(arr1, arr2):
    i, j = 0, 0
    while i < len(arr1) and j < len(arr2):
        yield arr1[i]
        yield arr2[j]
        i += 1
        j += 1
    
    while i < len(arr1):
        yield arr1[i]
        i += 1
    
    while j < len(arr2):
        yield arr2[j]
        j += 1

def ensureTuple(result):
    return result if isinstance(result, tuple) else (result, None)

def unpackEnvProps(envProps):
    envValue = envProps[0]
    validate = envProps[1] if len(envProps) > 1 else None
    requiresPreviousSuccess = envProps[2] if len(envProps) > 2 else False
    return envValue, validate, requiresPreviousSuccess

def checkRequiredEnvs(requiredEnvs):
    previousSuccess = True
    for envName, envProps in requiredEnvs.items():
        envValue, validate, requiresPreviousSuccess = unpackEnvProps(envProps)
        
        if envValue is None or envValue == "":
            print(f"Error: {envName} is missing. Please check your .env file.")
            previousSuccess = False
        elif (previousSuccess or not requiresPreviousSuccess) and validate:
            success, message = ensureTuple(validate())
            if not success:
                print(f"Error: {envName} is invalid. {message or 'Please check your .env file.'}")
                previousSuccess = False
            else:
                previousSuccess = True
        else:
            previousSuccess = True