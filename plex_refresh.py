import os
import requests
from shared.shared import plex

isRadarr = not not os.getenv('radarr_eventtype')

refreshEndpoint = f"{plex['serverHost']}/library/sections/{plex['serverMovieLibraryId'] if isRadarr else plex['serverTvShowLibraryId']}/refresh?X-Plex-Token={plex['serverApiKey']}"
cancelRefreshRequest = requests.delete(refreshEndpoint, headers={'Accept': 'application/json'})
refreshRequest = requests.get(refreshEndpoint, headers={'Accept': 'application/json'})

exit(0)