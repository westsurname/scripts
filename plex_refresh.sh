#!/bin/bash

cd "$(dirname "$0")"

exec &>> logs/plex_refresh.log

set -a
. .env
set +a

isRadarr=false
if [ -n "$radarr_eventtype" ]; then
  isRadarr=true
fi

if $isRadarr; then
  libraryId=$PLEX_SERVER_MOVIE_LIBRARY_ID
else
  libraryId=$PLEX_SERVER_TV_SHOW_LIBRARY_ID
fi

refreshEndpoint="$PLEX_SERVER_HOST/library/sections/$libraryId/refresh?X-Plex-Token=$PLEX_SERVER_API_KEY"

cancelRefreshRequest=$(curl -X DELETE "$refreshEndpoint" -H 'Accept: application/json')
refreshRequest=$(curl -X GET "$refreshEndpoint" -H 'Accept: application/json')