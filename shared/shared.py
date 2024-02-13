import os
# from dotenv import load_dotenv
from environs import Env

# load_dotenv()
env = Env()
env.read_env()

watchlist = {
    'plexProduct': os.getenv('WATCHLIST_PLEX_PRODUCT'),
    'plexVersion':os.getenv('WATCHLIST_PLEX_VERSION'),
    'plexClientIdentifier': os.getenv('WATCHLIST_PLEX_CLIENT_IDENTIFIER')
}

blackhole = {
    'baseWatchPath': os.getenv('BLACKHOLE_BASE_WATCH_PATH'),
    'radarrPath': os.getenv('BLACKHOLE_RADARR_PATH'),
    'sonarrPath': os.getenv('BLACKHOLE_SONARR_PATH'),
    'failIfNotCached': env.bool('BLACKHOLE_FAIL_IF_NOT_CACHED'),
    'rdMountRefreshSeconds': env.int('BLACKHOLE_RD_MOUNT_REFRESH_SECONDS'),
    'rdMountTorrentsPath': os.getenv('BLACKHOLE_RD_MOUNT_TORRENTS_PATH'),
    'waitForTorrentTimeout': env.int('BLACKHOLE_WAIT_FOR_TORRENT_TIMEOUT'),
    'historyPageSize': env.int('BLACKHOLE_HISTORY_PAGE_SIZE'),
}

server = {
    'host': os.getenv('SERVER_DOMAIN') 
}

plex = {
    'host': os.getenv('PLEX_HOST'),
    'metadataHost': os.getenv('PLEX_METADATA_HOST'),
    'serverHost': os.getenv('PLEX_SERVER_HOST'),
    'serverMachineId': os.getenv('PLEX_SERVER_MACHINE_ID'),
    'serverApiKey': os.getenv('PLEX_SERVER_API_KEY'),
    'serverMovieLibraryId': os.getenv('PLEX_SERVER_MOVIE_LIBRARY_ID'),
    'serverTvShowLibraryId': os.getenv('PLEX_SERVER_TV_SHOW_LIBRARY_ID')
}

overseerr = {
    'host': os.getenv('OVERSEERR_HOST'),
    'apiKey': os.getenv('OVERSEERR_API_KEY')
}

sonarr = {
    'host': os.getenv('SONARR_HOST'),
    'apiKey': os.getenv('SONARR_API_KEY')
}

radarr = {
    'host': os.getenv('RADARR_HOST'),
    'apiKey': os.getenv('RADARR_API_KEY')
}

tautulli = {
    'host': os.getenv('TAUTULLI_HOST'),
    'apiKey': os.getenv('TAUTULLI_API_KEY')
}

realdebrid = {
    'host': os.getenv('REALDEBRID_HOST'),
    'apiKey': os.getenv('REALDEBRID_API_KEY')
}

trakt = {
    'apiKey': os.getenv('TRAKT_API_KEY')
}

pushbullet = {
    'apiKey': os.getenv('PUSHBULLET_API_KEY')
}

discord = {
    'webhookUrl': os.getenv('DISCORD_WEBHOOK_URL')
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
