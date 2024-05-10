import os
import re
from environs import Env

env = Env()
env.read_env()

@env.parser_for("string")
def stringEnvParser(value):
    default_pattern = r"<[a-z0-9_]+>"
    if re.match(default_pattern, value):
        return None
    return value

watchlist = {
    'plexProduct': env.string('WATCHLIST_PLEX_PRODUCT'),
    'plexVersion': env.string('WATCHLIST_PLEX_VERSION'),
    'plexClientIdentifier': env.string('WATCHLIST_PLEX_CLIENT_IDENTIFIER')
}

blackhole = {
    'baseWatchPath': env.string('BLACKHOLE_BASE_WATCH_PATH'),
    'radarrPath': env.string('BLACKHOLE_RADARR_PATH'),
    'sonarrPath': env.string('BLACKHOLE_SONARR_PATH'),
    'failIfNotCached': env.bool('BLACKHOLE_FAIL_IF_NOT_CACHED'),
    'rdMountRefreshSeconds': env.int('BLACKHOLE_RD_MOUNT_REFRESH_SECONDS'),
    'rdMountTorrentsPath': env.string('BLACKHOLE_RD_MOUNT_TORRENTS_PATH'),
    'waitForTorrentTimeout': env.int('BLACKHOLE_WAIT_FOR_TORRENT_TIMEOUT'),
    'historyPageSize': env.int('BLACKHOLE_HISTORY_PAGE_SIZE'),
}

server = {
    'host': env.string('SERVER_DOMAIN') 
}

plex = {
    'host': env.string('PLEX_HOST'),
    'metadataHost': env.string('PLEX_METADATA_HOST'),
    'serverHost': env.string('PLEX_SERVER_HOST'),
    'serverMachineId': env.string('PLEX_SERVER_MACHINE_ID'),
    'serverApiKey': env.string('PLEX_SERVER_API_KEY'),
    'serverMovieLibraryId': env.string('PLEX_SERVER_MOVIE_LIBRARY_ID'),
    'serverTvShowLibraryId': env.string('PLEX_SERVER_TV_SHOW_LIBRARY_ID')
}

overseerr = {
    'host': env.string('OVERSEERR_HOST'),
    'apiKey': env.string('OVERSEERR_API_KEY')
}

sonarr = {
    'host': env.string('SONARR_HOST'),
    'apiKey': env.string('SONARR_API_KEY')
}

radarr = {
    'host': env.string('RADARR_HOST'),
    'apiKey': env.string('RADARR_API_KEY')
}

tautulli = {
    'host': env.string('TAUTULLI_HOST'),
    'apiKey': env.string('TAUTULLI_API_KEY')
}

realdebrid = {
    'host': env.string('REALDEBRID_HOST'),
    'apiKey': env.string('REALDEBRID_API_KEY')
}

trakt = {
    'apiKey': env.string('TRAKT_API_KEY')
}

discord = {
    'enabled': env.bool('DISCORD_ENABLED'),
    'updateEnabled': env.bool('DISCORD_UPDATE_ENABLED'),
    'webhookUrl': env.string('DISCORD_WEBHOOK_URL')
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

def checkRequiredEnvs(requiredEnvs):
    for envName, envValue in requiredEnvs.items():
        if not envValue:
            print(f"Error: {envName} is missing. Please check your .env file.")