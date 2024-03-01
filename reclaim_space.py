import os
import json
import requests
from datetime import datetime
from shared.shared import sonarr, radarr, overseerr, tautulli, trakt
from shared.discord import discordUpdate, discordError
import FsQuota

tautulliHost = tautulli['host']
tautulliAPIkey = tautulli['apiKey']

radarrHost = radarr['host']
radarrAPIkey = radarr['apiKey']

sonarrHost = sonarr['host']
sonarrAPIkey = sonarr['apiKey']

overseerrHost = overseerr['host']
overseerrAPIkey = overseerr['apiKey']

traktAPIkey = trakt['apiKey']

# This is the section ID for movies in your Tautulli config
tautulliMovieSectionID = "1"

# This is the section ID for shows in your Tautulli config
tautulliShowSectionID = "2"

# The number of rows you want to return from Tautulli's media_info table
tautulliNumRows = "2000"

# Number of days since last watch to delete
daysSinceLastWatch = 20

# Number of days since last added and nobody has watched
daysWithoutWatch = 10

# Radarr tag to ignore
radarrTagID = 2

# Sonarr tag to ignore
sonarrTagID = 2

# Number of days to ignore above tags
daysToIngoreTags = 30

# Amount to delete in GB
deleteSize = 200

# Minimum available space in GB allowed
minSpace = 200

# Dry-run
dryRun = False

## END USER VARIABLES

print(datetime.now().isoformat())

def purgeMovie(movie, movieTatulli):
  deletesize = 0

  f = requests.get(f"{radarrHost}/api/v3/movie?apiKey={radarrAPIkey}")
  try:
   guids = movieTatulli['guids']
   tmdbId = next(guid[len('tmdb://'):] for guid in guids if guid.startswith('tmdb://'))
   
   r = requests.get(f"{radarrHost}/api/v3/movie/lookup?apiKey={radarrAPIkey}&term=tmdb:{tmdbId}")
   radarr = r.json()[0]

   if radarrTagID in radarr['tags']and round((today - int(movie['added_at']))/86400) <= daysToIngoreTags:
    # print("SKIPPED: " + movie['title'] + " | Added at: " +  datetime.fromtimestamp(int(movie['added_at'])).isoformat() + " | Radarr ID: " + str(radarr['id']) + " | TMDB ID: " + str(radarr['tmdbId']))
    pass
   else:
    if not dryRun:
      response = requests.delete(f"{radarrHost}/api/v3/movie/" + str(radarr['id']) + f"?apiKey={radarrAPIkey}&deleteFiles=true")

    headers = {"X-Api-Key": f"{overseerrAPIkey}"}
    o = requests.get(f"{overseerrHost}/api/v1/movie/" + str(radarr['tmdbId']), headers=headers)
    overseerr = json.loads(o.text)
    if overseerr.get('mediaInfo', False):
      o = requests.delete(f"{overseerrHost}/api/v1/media/" + str(overseerr['mediaInfo']['id']), headers=headers)

    print("DELETED: " + movie['title'] + " | Radarr ID: " + str(radarr['id']) + " | TMDB ID: " + str(radarr['tmdbId']))
    deletesize = (int(movie['file_size'])/1073741824)
  except Exception as e:
   print("ERROR: " + movie['title'] + ": " + repr(e))

  return deletesize

def purgeSeason(season, tautulliShow):
  deletesize = 0

# Remove the below?
  f = requests.get(f"{sonarrHost}/api/v3/series?apiKey={sonarrAPIkey}")
  try:
   guids = tautulliShow['guids']
   tvdbId = next(guid[len('tvdb://'):] for guid in guids if guid.startswith('tvdb://'))
      
   s = requests.get(f"{sonarrHost}/api/v3/series/lookup?apiKey={sonarrAPIkey}&term=tvdb:{tvdbId}")
   show = s.json()[0]

   headers = {
     "trakt-api-key": f"{traktAPIkey}",
     "trakt-api-version": "2"
   }
   t = requests.get(f"https://api.trakt.tv/search/tvdb/{tvdbId}?type=show", headers=headers)
   trakt = json.loads(t.text)

   f = requests.get(f"{sonarrHost}/api/v3/episode?apiKey={sonarrAPIkey}&seriesId={show['id']}")
   episodes = f.json()

   for episode in episodes:
    if str(episode['seasonNumber']) != season['media_index'] or not episode['episodeFileId']: 
      # print("SKIPPED: " + season['parent_title'] + " - " + episode['title'] +  " | Sonarr ID: " + str(episode['id']) + " | TVDB ID: " + str(episode['tvdbId']))
      continue
    if episode['seasonNumber'] == 1 and episode['episodeNumber'] == 1 and radarrTagID in show['tags'] and round((today - int(season['added_at']))/86400) <= daysToIngoreTags:
      # print("SKIPPED: " + season['parent_title'] + " - " + episode['title'] + " | Added at: " +  datetime.fromtimestamp(int(season['added_at'])).isoformat() + " | Sonarr ID: " + str(episode['id']) + " | TVDB ID: " + str(episode['tvdbId']))
      continue
     
    episodeFile = requests.get(f"{sonarrHost}/api/v3/episodefile/{episode['episodeFileId']}?apiKey={sonarrAPIkey}").json()
    if not dryRun:
      response = requests.delete(f"{sonarrHost}/api/v3/episodefile/{episode['episodeFileId']}?apiKey={sonarrAPIkey}")

    print("DELETED: " + season['parent_title'] + " - " + episode['title'] + " | Sonarr ID: " + str(episode['id']) + " | TVDB ID: " + str(episode['tvdbId']))

    deletesize += (int(episodeFile['size'])/1073741824)

   seasonInfo = next(seasonInfo for seasonInfo in show['seasons'] if str(seasonInfo['seasonNumber']) == season['media_index'])
   seasonInfo['monitored'] = False

   response = requests.put(f"{sonarrHost}/api/v3/series/{show['id']}?apiKey={sonarrAPIkey}", json=show)

   headers = {"X-Api-Key": f"{overseerrAPIkey}"}

   o = requests.get(f"{overseerrHost}/api/v1/tv/" + str(trakt[0]['show']['ids']['tmdb']), headers=headers)
   overseerr = json.loads(o.text)
   if overseerr.get('mediaInfo', False):
    #  Delete the entire show until we figure out how to delete indiviual seasons
     o = requests.delete(f"{overseerrHost}/api/v1/media/" + str(overseerr['mediaInfo']['id']), headers=headers).json

  except Exception as e:
   print("ERROR: " + season['parent_title'] + ": " + repr(e))

  return deletesize

def getRemaining():
  quota = FsQuota.Quota('../').query(os.getuid())
  remaining = (quota.bhard - quota.bcount)/1000000 #1048576
  return remaining

today = round(datetime.now().timestamp())

remaining = getRemaining()
if (remaining > minSpace):
  print(f"Cancelling. Remaining space: {remaining}GB. Minimum alllowed space: {minSpace}GB")  
else:
  print(f"Running. Remaining space: {remaining}GB. Minimum alllowed space: {minSpace}GB")  
  totalsize = 0

  r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_library_media_info&section_id={tautulliShowSectionID}&length={tautulliNumRows}&refresh=true&order_column=added_at&order_dir=asc")
  shows = json.loads(r.text)


  for show in shows['response']['data']['data']:
    r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_metadata&section_id={tautulliShowSectionID}&rating_key={show['rating_key']}&media_type=show")
    show = json.loads(r.text)['response']['data']

    r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_children_metadata&section_id={tautulliShowSectionID}&rating_key={show['rating_key']}&media_type=show")
    seasons = json.loads(r.text)
    
    for season in seasons['response']['data']['children_list']:
      r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_history&section_id={tautulliShowSectionID}&parent_rating_key={season['rating_key']}&media_type=episode&length=1000")
      episodePlays = json.loads(r.text)['response']['data']['data']
      lastPlays = [episodePlay['stopped'] for episodePlay in episodePlays]

      if any(lastPlays):
        lp = round((today - int(max(lastPlays)))/86400)
        if lp > daysSinceLastWatch:
          totalsize = totalsize + purgeSeason(season, show) 
      else:
        if season['added_at']:
          aa = round((today - int(season['added_at']))/86400)
          if aa > daysWithoutWatch:
            totalsize = totalsize + purgeSeason(season, show)

      if totalsize >= deleteSize: break

    if totalsize >= deleteSize: break



  r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_library_media_info&section_id={tautulliMovieSectionID}&length={tautulliNumRows}&refresh=true&order_column=added_at&order_dir=asc")
  movies = json.loads(r.text)


  for movie in movies['response']['data']['data']:  
    r = requests.get(f"{tautulliHost}/api/v2/?apikey={tautulliAPIkey}&cmd=get_metadata&section_id={tautulliMovieSectionID}&rating_key={movie['rating_key']}&media_type=movie")
    movieMeta = json.loads(r.text)['response']['data']

    if movie['last_played']: 
      lp = round((today - int(movie['last_played']))/86400)
      if lp > daysSinceLastWatch:
        totalsize = totalsize + purgeMovie(movie, movieMeta) 
    else:
      if movie['added_at']:
        aa = round((today - int(movie['added_at']))/86400)
        if aa > daysWithoutWatch:
          totalsize = totalsize + purgeMovie(movie, movieMeta) 
        
    if totalsize >= deleteSize * 2: break


  print("Total space reclaimed: " + str("{:.2f}".format(totalsize)) + "GB")

  try:
    remaining = getRemaining()
    if (remaining < minSpace):
      # Consider running again with stricter requirements and/or pausing downloads in sabnzbd
      discordError("Running low on space", f"Remaining space: {remaining}GB.")
  except Exception as e:
   print("ERROR: " + repr(e))
    