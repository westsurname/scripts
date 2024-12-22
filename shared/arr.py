from abc import ABC, abstractmethod
from typing import Type, List
import requests
from shared.shared import sonarr, radarr, checkRequiredEnvs
from shared.requests import retryRequest

def validateSonarrHost():
    url = f"{sonarr['host']}/login"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False

def validateSonarrApiKey():
    url = f"{sonarr['host']}/api/v3/system/status?apikey={sonarr['apiKey']}"
    try:
        response = requests.get(url)
        if response.status_code == 401:
            return False, "Invalid or expired API key."
    except Exception as e:
        return False
    
    return True

def validateRadarrHost():
    url = f"{radarr['host']}/login"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False

def validateRadarrApiKey():
    url = f"{radarr['host']}/api/v3/system/status?apikey={radarr['apiKey']}"
    try:
        response = requests.get(url)
        if response.status_code == 401:
            return False, "Invalid or expired API key."
    except Exception as e:
        return False
    
    return True

requiredEnvs = {
    'Sonarr host': (sonarr['host'], validateSonarrHost),
    'Sonarr API key': (sonarr['apiKey'], validateSonarrApiKey, True),
    'Radarr host': (radarr['host'], validateRadarrHost),
    'Radarr API key': (radarr['apiKey'], validateRadarrApiKey, True)
}

checkRequiredEnvs(requiredEnvs)

class Media(ABC):
    def __init__(self, json) -> None:
        super().__init__()
        self.json = json

    @property 
    @abstractmethod
    def size(self):
        pass

    @property
    def id(self):
        return self.json['id']

    @property
    def title(self):
        return self.json['title']
    
    @property
    def path(self):
        return self.json['path']
    
    @path.setter
    def path(self, path):
        self.json['path'] = path

    @property
    def anyMonitoredChildren(self):
        return bool(self.monitoredChildrenIds)

    @property
    def anyFullyAvailableChildren(self):
        return bool(self.fullyAvailableChildrenIds)
    
    @property
    def childrenIds(self):
        pass

    @property
    @abstractmethod
    def monitoredChildrenIds(self):
        pass

    @property
    @abstractmethod
    def fullyAvailableChildrenIds(self):
        pass

    @abstractmethod
    def setChildMonitored(self, childId: int, monitored: bool):
        pass

class Movie(Media):
    @property
    def size(self):
        return self.json['sizeOnDisk']
    
    @property
    def childrenIds(self):
        return [self.id]

    @property
    def monitoredChildrenIds(self):
        return [self.id] if self.json['monitored'] else []

    @property
    def fullyAvailableChildrenIds(self):
        return [self.id] if self.json['hasFile'] else []
    
    def setChildMonitored(self, childId: int, monitored: bool):
        self.json["monitored"] = monitored

class Show(Media):
    @property
    def size(self):
        return self.json['statistics']['sizeOnDisk']
    
    @property
    def childrenIds(self):
        return [season['seasonNumber'] for season in self.json['seasons']]

    @property
    def monitoredChildrenIds(self):
        return [season['seasonNumber'] for season in self.json['seasons'] if season['monitored']]

    @property
    def fullyAvailableChildrenIds(self):
        return [season['seasonNumber'] for season in self.json['seasons'] if season['statistics']['percentOfEpisodes'] == 100]

    def setChildMonitored(self, childId: int, monitored: bool):
        for season in self.json['seasons']:
            if season['seasonNumber'] == childId:
                season['monitored'] = monitored
                break

class MediaFile(ABC):
    def __init__(self, json) -> None:
        super().__init__()
        self.json = json

    @property
    def id(self):
        return self.json['id']

    @property
    def path(self):
        return self.json['path']

    @property
    def quality(self):
        return self.json['quality']['quality']['name']

    @property
    def size(self):
        return self.json['size']

    @property
    @abstractmethod
    def parentId(self):
        pass

class EpisodeFile(MediaFile):
    @property
    def parentId(self):
        return self.json['seasonNumber']

class MovieFile(MediaFile):
    @property
    def parentId(self):
        return self.json['movieId']


class MediaHistory(ABC):
    def __init__(self, json) -> None:
        super().__init__()
        self.json = json

    @property
    def eventType(self):
        return self.json['eventType']

    @property
    def reason(self):
        return self.json['data'].get('reason')

    @property
    def quality(self):
        return self.json['quality']['quality']['name']

    @property
    def id(self):
        return self.json['id']

    @property
    def sourceTitle(self):
        return self.json['sourceTitle']

    @property
    def torrentInfoHash(self):
        return self.json['data'].get('torrentInfoHash')

    @property
    def releaseType(self):
        """Get the release type from the history item data."""
        return self.json['data'].get('releaseType')

    @property
    @abstractmethod
    def parentId(self):
        pass

    @property
    @abstractmethod
    def grandparentId(self):
        """Get the top-level ID (series ID for episodes, same as parentId for movies)."""
        pass

    @property
    @abstractmethod
    def isFileDeletedEvent(self):
        pass

class MovieHistory(MediaHistory):
    @property
    def parentId(self):
        return self.json['movieId']

    @property
    def grandparentId(self):
        """For movies, grandparent ID is the same as parent ID."""
        return self.parentId

    @property
    def isFileDeletedEvent(self):
        return self.eventType == 'movieFileDeleted'

class EpisodeHistory(MediaHistory):
    @property
    # Requires includeGrandchildDetails to be true
    def parentId(self):
        return self.json['episode']['seasonNumber']

    @property
    def grandparentId(self):
        """Get the series ID from the history item."""
        return self.json['episode']['seriesId']

    @property
    def isFileDeletedEvent(self):
        return self.eventType == 'episodeFileDeleted'
    
class Arr(ABC):
    def __init__(self, host: str, apiKey: str, endpoint: str, fileEndpoint: str, childIdName: str, childName: str, grandchildName: str, constructor: Type[Media], fileConstructor: Type[MediaFile], historyConstructor: Type[MediaHistory]) -> None:
        self.host = host
        self.apiKey = apiKey
        self.endpoint = endpoint
        self.fileEndpoint = fileEndpoint
        self.childIdName = childIdName
        self.childName = childName
        self.grandchildName = grandchildName
        self.constructor = constructor
        self.fileConstructor = fileConstructor
        self.historyConstructor = historyConstructor

    def get(self, id: int):
        response = retryRequest(lambda: requests.get(f"{self.host}/api/v3/{self.endpoint}/{id}?apiKey={self.apiKey}"))
        return self.constructor(response.json())

    def getAll(self):
        response = retryRequest(lambda: requests.get(f"{self.host}/api/v3/{self.endpoint}?apiKey={self.apiKey}"))
        return map(self.constructor, response.json())

    def put(self, media: Media):
        retryRequest(lambda: requests.put(f"{self.host}/api/v3/{self.endpoint}/{media.id}?apiKey={self.apiKey}&moveFiles=true", json=media.json))

    def getFiles(self, media: Media, childId: int=None):
        response = retryRequest(lambda: requests.get(f"{self.host}/api/v3/{self.fileEndpoint}?apiKey={self.apiKey}&{self.endpoint}Id={media.id}"))

        files = map(self.fileConstructor, response.json())

        if childId != None and childId != media.id:
            files = filter(lambda file: file.parentId == childId, files)

        return files

    def deleteFiles(self, files: List[MediaFile]):
        fileIds = [file.id for file in files]
        response = retryRequest(lambda: requests.delete(f"{self.host}/api/v3/{self.fileEndpoint}/bulk?apiKey={self.apiKey}", json={f"{self.fileEndpoint}ids": fileIds}))
        
        return response.json()

    def getHistory(self, pageSize: int=None, includeGrandchildDetails: bool=False, media: Media=None, childId: int=None):
        endpoint = f"/{self.endpoint}" if media else ''
        pageSizeParam = f"pageSize={pageSize}&" if pageSize else ''
        includeGrandchildDetailsParam = f"include{self.grandchildName}=true&" if includeGrandchildDetails else ''
        idParam = f"{self.endpoint}Id={media.id}&" if media else ''
        childIdParam = f"{self.childIdName}={childId}&" if media and childId != None and childId != media.id else ''
        response = retryRequest(lambda: requests.get(f"{self.host}/api/v3/history{endpoint}?{pageSizeParam}{includeGrandchildDetailsParam}{idParam}{childIdParam}apiKey={self.apiKey}"))
        
        history = response.json()

        return map(self.historyConstructor, history['records'] if isinstance(history, dict) else history)
    
    def failHistoryItem(self, historyId: int):
        retryRequest(lambda: requests.post(f"{self.host}/api/v3/history/failed/{historyId}?apiKey={self.apiKey}"))

    def refreshMonitoredDownloads(self):
        retryRequest(lambda: requests.post(f"{self.host}/api/v3/command?apiKey={self.apiKey}", json={'name': 'RefreshMonitoredDownloads'}, headers={'Content-Type': 'application/json'}))

    def interactiveSearch(self, media: Media, childId: int):
        response = retryRequest(lambda: requests.get(f"{self.host}/api/v3/release?apiKey={self.apiKey}&{self.endpoint}Id={media.id}{f'&{self.childIdName}={childId}' if childId != media.id else ''}"))
        return response.json()

    def automaticSearch(self, media: Media, childId: int):
        response = retryRequest(lambda: requests.post(
            f"{self.host}/api/v3/command?apiKey={self.apiKey}", 
            json=self._automaticSearchJson(media, childId), 
        ))
        return response.json()

    def _automaticSearchJson(self, media: Media, childId: int):
        pass

class Sonarr(Arr):
    host = sonarr['host']
    apiKey = sonarr['apiKey']
    endpoint = 'series'
    fileEndpoint = 'episodefile'
    childIdName = 'seasonNumber'
    childName = 'Season'
    grandchildName = 'Episode'

    def __init__(self) -> None:
        super().__init__(Sonarr.host, Sonarr.apiKey, Sonarr.endpoint, Sonarr.fileEndpoint, Sonarr.childIdName, Sonarr.childName, Sonarr.grandchildName, Show, EpisodeFile, EpisodeHistory)

    def _automaticSearchJson(self, media: Media, childId: int):
        return {"name": f"{self.childName}Search", f"{self.endpoint}Id": media.id, self.childIdName: childId}

class Radarr(Arr):
    host = radarr['host']
    apiKey = radarr['apiKey']
    endpoint = 'movie'
    fileEndpoint = 'moviefile'
    childIdName = None
    childName = 'Movies'
    grandchildName = 'Movie'

    def __init__(self) -> None:
        super().__init__(Radarr.host, Radarr.apiKey, Radarr.endpoint, Radarr.fileEndpoint, Radarr.childIdName, Radarr.childName, Radarr.grandchildName, Movie, MovieFile, MovieHistory)

    def _automaticSearchJson(self, media: Media, childId: int):
        return {"name": f"{self.childName}Search", f"{self.endpoint}Ids": [media.id]}
