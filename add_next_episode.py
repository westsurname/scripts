import requests
import sys
from shared.shared import sonarr


sonarrHost = sonarr['host']
sonarrAPIkey = sonarr['apiKey']

show_tvdbId = sys.argv[1]
ep_num = int(sys.argv[2])
season_num = int(sys.argv[3])

s = requests.get(f"{sonarrHost}/api/v3/series/lookup?apiKey={sonarrAPIkey}&term=tvdb:{show_tvdbId}")
sonarrShow = s.json()

s = requests.get(f"{sonarrHost}/api/v3/episode?apiKey={sonarrAPIkey}&seriesId={sonarrShow[0]['id']}")
sonarrEpisodes = s.json()

sonarrEpisode = next(filter(lambda episode: episode['seasonNumber'] == season_num and ep_num + 1 == episode['episodeNumber'], sonarrEpisodes))

if (sonarrEpisode and 
    sonarrEpisode['hasFile'] == False):
    monitorJson = {'episodeIds': [sonarrEpisode['id']], 'monitored': True}
    s = requests.put(f"{sonarrHost}/api/v3/episode/monitor?apiKey={sonarrAPIkey}", json=monitorJson)
    
    searchJson = {'name': 'EpisodeSearch', 'episodeIds': [sonarrEpisode['id']]}
    s = requests.post(f"{sonarrHost}/api/v3/command?apiKey={sonarrAPIkey}", json=searchJson)
