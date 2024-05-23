import os
import re
import hashlib
import bencode3
import requests
from abc import ABC, abstractmethod
from urllib.parse import urljoin
from shared.discord import discordUpdate
from shared.shared import realdebrid, torbox, mediaExtensions, checkRequiredEnvs
from werkzeug.utils import cached_property

def validateDebridEnabled():
    if not realdebrid['enabled'] and not torbox['enabled']:
        return False, "At least one of RealDebrid or Torbox must be enabled."
    return True

def validateRealdebridHost():
    url = urljoin(realdebrid['host'], "time")
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False
    
def validateRealdebridApiKey():
    url = urljoin(realdebrid['host'], "user")
    headers = {'Authorization': f'Bearer {realdebrid["apiKey"]}'}
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 401:
            return False, "Invalid or expired API key."
        elif response.status_code == 403:
            return False, "Permission denied, account locked."
    except Exception as e:
        return False
    
    return True

def validateRealdebridMountTorrentsPath():
    path = realdebrid['mountTorrentsPath']
    if os.path.exists(path) and any(os.path.isdir(os.path.join(path, child)) for child in os.listdir(path)):
        return True
    else:
        return False, "Path does not exist or has no children."

def validateTorboxHost():
    url = urljoin(torbox['host'], "stats")
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False
    
def validateTorboxApiKey():
    url = urljoin(torbox['host'], "user/me")
    headers = {'Authorization': f'Bearer {torbox["apiKey"]}'}
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 401:
            return False, "Invalid or expired API key."
        elif response.status_code == 403:
            return False, "Permission denied, account locked."
    except Exception as e:
        return False
    
    return True

def validateTorboxMountTorrentsPath():
    path = torbox['mountTorrentsPath']
    if os.path.exists(path) and any(os.path.isdir(os.path.join(path, child)) for child in os.listdir(path)):
        return True
    else:
        return False, "Path does not exist or has no children."

requiredEnvs = {
    'RealDebrid/TorBox enabled': (True, validateDebridEnabled),
}

if realdebrid['enabled']:
    requiredEnvs.update({
        'RealDebrid host': (realdebrid['host'], validateRealdebridHost),
        'RealDebrid API key': (realdebrid['apiKey'], validateRealdebridApiKey, True),
        'RealDebrid mount torrents path': (realdebrid['mountTorrentsPath'], validateRealdebridMountTorrentsPath)
    })

if torbox['enabled']:
    requiredEnvs.update({
        'Torbox host': (torbox['host'], validateTorboxHost),
        'Torbox API key': (torbox['apiKey'], validateTorboxApiKey, True),
        'Torbox mount torrents path': (torbox['mountTorrentsPath'], validateTorboxMountTorrentsPath)
    })

checkRequiredEnvs(requiredEnvs)

class TorrentBase(ABC):
    STATUS_WAITING_FILES_SELECTION = 'waiting_files_selection'
    STATUS_DOWNLOADING = 'downloading'
    STATUS_COMPLETED = 'completed'
    STATUS_ERROR = 'error'

    def __init__(self, f, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__()
        self.f = f
        self.file = file
        self.failIfNotCached = failIfNotCached
        self.onlyLargestFile = onlyLargestFile
        self.incompatibleHashSize = False
        self.id = None
        self._info = None
        self._hash = None
        self._instantAvailability = None
    
    def print(self, *values: object):
        print(f"[{self.__class__.__name__} - {self.file.fileInfo.filenameWithoutExt}]", *values)

    @cached_property
    def fileData(self):
        fileData = self.f.read()
        self.f.seek(0)
        return fileData

    @abstractmethod
    def submitTorrent(self):
        pass

    @abstractmethod
    def getHash(self):
        pass
    
    @abstractmethod
    def addTorrent(self):
        pass
    
    @abstractmethod
    def getInfo(self, refresh=False):
        pass

    @abstractmethod
    def selectFiles(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    def _addTorrentFile(self):
        pass

    def _addMagnetFile(self):
        pass

    def _enforceId(self):
        if not self.id:
            raise Exception("Id is required. Must be acquired via successfully running submitTorrent() first.")

class RealDebrid(TorrentBase):
    def __init__(self, f, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__(f, file, failIfNotCached, onlyLargestFile)
        self.headers = {'Authorization': f'Bearer {realdebrid["apiKey"]}'}
        self.mountTorrentsPath = realdebrid["mountTorrentsPath"]

    def submitTorrent(self):
        if self.failIfNotCached:
            instantAvailability = self._getInstantAvailability()
            self.print('instantAvailability:', not not instantAvailability)
            if not instantAvailability:
                return False

        self.addTorrent()
        return True

    def _getInstantAvailability(self, refresh=False):
        if refresh or not self._instantAvailability:
            torrentHash = self.getHash()
            self.print('hash:', torrentHash)

            if len(torrentHash) != 40:
                self.incompatibleHashSize = True
                return True

            instantAvailabilityRequest = requests.get(urljoin(realdebrid['host'], f"torrents/instantAvailability/{torrentHash}"), headers=self.headers)
            instantAvailabilities = instantAvailabilityRequest.json()
            self.print('instantAvailabilities:', instantAvailabilities)
            instantAvailabilityHosters = next(iter(instantAvailabilities.values()))
            if not instantAvailabilityHosters: return

            self._instantAvailability = next(iter(instantAvailabilityHosters.values()))

        return self._instantAvailability
    
    def _getAvailableHost(self):
        availableHostsRequest = requests.get(urljoin(realdebrid['host'], "torrents/availableHosts"), headers=self.headers)
        availableHosts = availableHostsRequest.json()
        return availableHosts[0]['host']
    
    def getInfo(self, refresh=False):
        self._enforceId()

        if refresh or not self._info:
            infoRequest = requests.get(urljoin(realdebrid['host'], f"torrents/info/{self.id}"), headers=self.headers)
            info = infoRequest.json()
            info['status'] = self._normalize_status(info['status'])
            self._info = info

        return self._info

    def selectFiles(self):
        self._enforceId()

        info = self.getInfo()
        self.print('files:', info['files'])
        mediaFiles = [file for file in info['files'] if os.path.splitext(file['path'])[1].lower() in mediaExtensions]
        
        if not mediaFiles:
            self.print('no media files found')
            return False

        mediaFileIds = {str(file['id']) for file in mediaFiles}
        self.print('required fileIds:', mediaFileIds)
        
        largestMediaFile = max(mediaFiles, key=lambda file: file['bytes'])
        largestMediaFileId = str(largestMediaFile['id'])
        self.print('only largest file:', self.onlyLargestFile)
        self.print('largest file:', largestMediaFile)

        if self.failIfNotCached and not self.incompatibleHashSize:
            targetFileIds = {largestMediaFileId} if self.onlyLargestFile else mediaFileIds
            if not any(set(fileGroup.keys()) == targetFileIds for fileGroup in self._instantAvailability):
                extraFilesGroup = next((fileGroup for fileGroup in self._instantAvailability if largestMediaFileId in fileGroup.keys()), None)
                if self.onlyLargestFile and extraFilesGroup:
                    self.print('extra files required for cache:', extraFilesGroup)
                    discordUpdate('Extra files required for cache:', extraFilesGroup)
                return False
            
        if self.onlyLargestFile and len(mediaFiles) > 1:
            discordUpdate('largest file:', largestMediaFile['path'])
                
        files = {'files': [largestMediaFileId] if self.onlyLargestFile else ','.join(mediaFileIds)}
        selectFilesRequest = requests.post(urljoin(realdebrid['host'], f"torrents/selectFiles/{self.id}"), headers=self.headers, data=files)
        
        return True

    def delete(self):
        self._enforceId()

        deleteRequest = requests.delete(urljoin(realdebrid['host'], f"torrents/delete/{self.id}"), headers=self.headers)

    def _addFile(self, endpoint, data):
        host = self._getAvailableHost()

        request = requests.post(urljoin(realdebrid['host'], endpoint), params={'host': host}, headers=self.headers, data=data)
        response = request.json()

        self.print('response info:', response)
        self.id = response['id']

        return self.id

    def _addTorrentFile(self):
        return self._addFile("torrents/addTorrent", self.f)

    def _addMagnetFile(self):
        return self._addFile("torrents/addMagnet", {'magnet': self.fileData})
    
    def _normalize_status(self, status):
        if status in ['waiting_files_selection']:
            return self.STATUS_WAITING_FILES_SELECTION
        elif status in ['magnet_conversion', 'queued', 'downloading', 'compressing', 'uploading']:
            return self.STATUS_DOWNLOADING
        elif status == 'downloaded':
            return self.STATUS_COMPLETED
        elif status in ['magnet_error', 'error', 'dead', 'virus']:
            return self.STATUS_ERROR
        return status

class Torbox(TorrentBase):
    def __init__(self, f, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__(f, file, failIfNotCached, onlyLargestFile)
        self.headers = {'Authorization': f'Bearer {torbox["apiKey"]}'}
        self.mountTorrentsPath = torbox["mountTorrentsPath"]

    def submitTorrent(self):
        if self.failIfNotCached:
            instantAvailability = self._getInstantAvailability()
            self.print('instantAvailability:', not not instantAvailability)
            if not instantAvailability:
                return False

        self.addTorrent()
        return True

    def _getInstantAvailability(self, refresh=False):
        if refresh or not self._instantAvailability:
            torrentHash = self.getHash()
            self.print('hash:', torrentHash)

            instantAvailabilityRequest = requests.get(
                urljoin(torbox['host'], "torrents/checkcached"),
                headers=self.headers,
                params={'hash': torrentHash, 'format': 'object'}
            )
            instantAvailabilities = instantAvailabilityRequest.json()
            self.print('instantAvailabilities:', instantAvailabilities)
            self._instantAvailability = instantAvailabilities['data']['data'] if 'data' in instantAvailabilities and 'data' in instantAvailabilities['data'] and instantAvailabilities['data']['data'] is not False else None
        
        return self._instantAvailability

    def getInfo(self, refresh=False):
        self._enforceId()

        if refresh or not self._info:
            infoRequest = requests.get(urljoin(torbox['host'], "torrents/mylist"), headers=self.headers)
            torrents = infoRequest.json()['data']
            for torrent in torrents:
                if torrent['id'] == self.id:
                    torrent['status'] = self._normalize_status(torrent['download_state'], torrent['download_finished'])
                    self._info = torrent
                    break

        return self._info

    def selectFiles(self):
        pass

    def delete(self):
        self._enforceId()

        deleteRequest = requests.delete(urljoin(torbox['host'], "torrents/controltorrent"), headers=self.headers, data={'torrent_id': self.id, 'operation': "Delete"})

    def _addFile(self, endpoint, data=None, files=None):
        request = requests.post(urljoin(torbox['host'], endpoint), headers=self.headers, data=data, files=files)
        
        response = request.json()
        self.print('response info:', response)
        self.id = response['data']['torrent_id']

        return self.id

    def _addTorrentFile(self):
        nametorrent = self.f.name.split('/')[-1]
        files = {'file': (nametorrent, self.f, 'application/x-bittorrent')}
        return self._addFile("/torrents/createtorrent", files=files)

    def _addMagnetFile(self):
        return self._addFile("/torrents/createtorrent", data={'magnet': self.fileData})

    def _normalize_status(self, status, download_finished):
        if download_finished:
            return self.STATUS_COMPLETED
        elif status in ['paused', 'downloading', 'uploading']:
            return self.STATUS_DOWNLOADING
        elif status in ['error', 'stalled (no seeds)']:
            return self.STATUS_ERROR
        return status

class Torrent(TorrentBase):
    def getHash(self):

        if not self._hash:
            self._hash = hashlib.sha1(bencode3.bencode(bencode3.bdecode(self.fileData)['info'])).hexdigest()
        
        return self._hash

    def addTorrent(self):
        self._addTorrentFile()

class Magnet(TorrentBase):
    def getHash(self):

        if not self._hash:
            # Consider changing when I'm more familiar with hashes
            self._hash = re.search('xt=urn:btih:(.+?)(?:&|$)', self.fileData).group(1)
        
        return self._hash
    
    def addTorrent(self):
        self._addMagnetFile()

class RealDebridTorrent(RealDebrid, Torrent):
    pass

class RealDebridMagnet(RealDebrid, Magnet):
    pass

class TorboxTorrent(Torbox, Torrent):
    pass

class TorboxMagnet(Torbox, Magnet):
    pass   