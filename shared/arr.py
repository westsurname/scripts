from abc import ABC, abstractmethod
from typing import Type
from shared.shared import sonarr, radarr
import requests


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

class Movie(Media):
    @property
    def size(self):
        return self.json['sizeOnDisk']

class Show(Media):
    @property
    def size(self):
        return self.json['statistics']['sizeOnDisk']


class Arr(ABC):
    def __init__(self, host: str, apiKey: str, endpoint: str, constructor: Type[Media]) -> None:
        self.host = host
        self.apiKey = apiKey
        self.endpoint = endpoint
        self.constructor = constructor

    def getAll(self):
        get = requests.get(f"{self.host}/api/v3/{self.endpoint}?apiKey={self.apiKey}")
        return map(self.constructor, get.json())

    def put(self, media: Media):
        put = requests.put(f"{self.host}/api/v3/{self.endpoint}/{media.id}?apiKey={self.apiKey}&moveFiles=true", json=media.json)

    def getHistory(self, pageSize: int):
        historyRequest = requests.get(f"{self.host}/api/v3/history?pageSize={pageSize}&apiKey={self.apiKey}")
        history = historyRequest.json()

        return history

    def failHistoryItem(self, historyId: int):
        failRequest = requests.post(f"{self.host}/api/v3/history/failed/{historyId}?apiKey={self.apiKey}")

    def refreshMonitoredDownloads(self):
        commandRequest = requests.post(f"{self.host}/api/v3/command?apiKey={self.apiKey}", json={'name': 'RefreshMonitoredDownloads'}, headers={'Content-Type': 'application/json'})

class Sonarr(Arr):
    host = sonarr['host']
    apiKey = sonarr['apiKey']
    endpoint = 'series'

    def __init__(self) -> None:
        super().__init__(Sonarr.host, Sonarr.apiKey, Sonarr.endpoint, Show)

class Radarr(Arr):
    host = radarr['host']
    apiKey = radarr['apiKey']
    endpoint = 'movie'

    def __init__(self) -> None:
        super().__init__(Radarr.host, Radarr.apiKey, Radarr.endpoint, Movie)