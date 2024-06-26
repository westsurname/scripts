from abc import ABC, abstractmethod
from typing import Type, List
import requests
from shared.shared import sonarr, radarr, lidarr, checkRequiredEnvs  # Added lidarr import

# Validation functions for Sonarr
def validateSonarrHost():
    url = f"{sonarr['host']}"
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

# Validation functions for Radarr
def validateRadarrHost():
    url = f"{radarr['host']}"
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

# Validation functions for Lidarr
def validateLidarrHost():
    url = f"{lidarr['host']}"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False

def validateLidarrApiKey():
    url = f"{lidarr['host']}/api/v1/system/status?apikey={lidarr['apiKey']}"
    try:
        response = requests.get(url)
        if response.status_code == 401:
            return False, "Invalid or expired API key."
    except Exception as e:
        return False
    
    return True

# Required environment variables with validations
requiredEnvs = {
    'Sonarr host': (sonarr['host'], validateSonarrHost),
    'Sonarr API key': (sonarr['apiKey'], validateSonarrApiKey, True),
    'Radarr host': (radarr['host'], validateRadarrHost),
    'Radarr API key': (radarr['apiKey'], validateRadarrApiKey, True),
    'Lidarr host': (lidarr['host'], validateLidarrHost),  # Added Lidarr host validation
    'Lidarr API key': (lidarr['apiKey'], validateLidarrApiKey, True)  # Added Lidarr API key validation
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

class TrackFile(MediaFile):
    @property
    def parentId(self):
        return self.json['albumId']

class Arr(ABC):
    def __init__(self, host: str, apiKey: str, endpoint: str, fileEndpoint: str, childIdName: str, childName: str, constructor: Type[Media], fileConstructor: Type[MediaFile]) -> None:
        self.host = host
        self.apiKey = apiKey
        self.endpoint = endpoint
        self.fileEndpoint = fileEndpoint
        self.childIdName = childIdName
        self.childName = childName
        self.constructor = constructor
        self.fileConstructor = fileConstructor

    def get(self, id: int):
        get = requests.get(f"{self.host}/api/v3/{self.endpoint}/{id}?apiKey={self.apiKey}")
        return self.constructor(get.json())

    def getAll(self):
        get = requests.get(f"{self.host}/api/v3/{self.endpoint}?apiKey={self.apiKey}")
        return map(self.constructor, get.json())

    def put(self, media: Media):
        put = requests.put(f"{self.host}/api/v3/{self.endpoint}/{media.id}?apiKey={self.apiKey}&moveFiles=true", json=media.json)

    def getFiles(self, media: Media):
        files = requests.get(f"{self.host}/api/v3/{self.fileEndpoint}?apiKey={self.apiKey}&{self.endpoint}Id={media.id}")   
        return map(self.fileConstructor, files.json())

    def deleteFiles(self, files: List[MediaFile]):
        fileIds = [file.id for file in files]
        delete = requests.delete(f"{self.host}/api/v3/{self.fileEndpoint}/bulk?apiKey={self.apiKey}", json={f"{self.fileEndpoint}ids": fileIds})

        return delete.json()

    def getHistory(self, pageSize: int):
        historyRequest = requests.get(f"{self.host}/api/v3/history?pageSize={pageSize}&apiKey={self.apiKey}")
        history = historyRequest.json()

        return history

    def failHistoryItem(self, historyId: int):
        failRequest = requests.post(f"{self.host}/api/v3/history/failed/{historyId}?apiKey={self.apiKey}")

    def refreshMonitoredDownloads(self):
        commandRequest = requests.post(f"{self.host}/api/v3/command?apiKey={self.apiKey}", json={'name': 'RefreshMonitoredDownloads'}, headers={'Content-Type': 'application/json'})

    def interactiveSearch(self, media: Media, childId: int):
        search = requests.get(f"{self.host}/api/v3/release?apiKey={self.apiKey}&{self.endpoint}Id={media.id}{f'&{self.childIdName}={childId}' if childId != media.id else ''}")
        return search.json()

    def automaticSearch(self, media: Media, childId: int):
        search = requests.post(
            f"{self.host}/api/v3/command?apiKey={self.apiKey}", 
            json=self._automaticSearchJson(media, childId), 
        )
        return search.json()

    def _automaticSearchJson(self, media: Media, childId: int):
        pass

class Sonarr(Arr):
    host = sonarr['host']
    apiKey = sonarr['apiKey']
    endpoint = 'series'
    fileEndpoint = 'episodefile'
    childIdName = 'seasonNumber'
    childName = 'Season'

    def __init__(self) -> None:
        super().__init__(Sonarr.host, Sonarr.apiKey, Sonarr.endpoint, Sonarr.fileEndpoint, Sonarr.childIdName, Sonarr.childName, Show, EpisodeFile)

    def _automaticSearchJson(self, media: Media, childId: int):
        return {"name": f"{self.childName}Search", f"{self.endpoint}Id": media.id, self.childIdName: childId}

class Radarr(Arr):
    host = radarr['host']
    apiKey = radarr['apiKey']
    endpoint = 'movie'
    fileEndpoint = 'moviefile'
    childIdName = None
    childName = 'Movies'

    def __init__(self) -> None:
        super().__init__(Radarr.host, Radarr.apiKey, Radarr.endpoint, Radarr.fileEndpoint, None, Radarr.childName, Movie, MovieFile)

    def _automaticSearchJson(self, media: Media, childId: int):
        return {"name": f"{self.childName}Search", f"{self.endpoint}Ids": [media.id]}

class Lidarr(Arr):
    host = lidarr['host']
    apiKey = lidarr['apiKey']
    endpoint = 'artist'
    fileEndpoint = 'trackfile'
    childIdName = 'albumId'
    childName = 'Album'

    def __init__(self) -> None:
        super().__init__(Lidarr.host, Lidarr.apiKey, Lidarr.endpoint, Lidarr.fileEndpoint, Lidarr.childIdName, Lidarr.childName, Album, TrackFile)

    def _automaticSearchJson(self, media: Media, childId: int):
        return {"name": f"{self.childName}Search", f"{self.endpoint}Id": media.id, self.childIdName: childId}

class Album(Media):
    @property
    def size(self):
        return self.json['statistics']['sizeOnDisk']

    @property
    def monitoredChildrenIds(self):
        return [album['id'] for album in self.json['albums'] if album['monitored']]

    @property
    def fullyAvailableChildrenIds(self):
        return [album['id'] for album in self.json['albums'] if album['statistics']['percentOfTracks'] == 100]

    def setChildMonitored(self, childId: int, monitored: bool):
        for album in self.json['albums']:
            if album['id'] == childId:
                album['monitored'] = monitored
                break
