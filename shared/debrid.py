import asyncio
import os
import re
import hashlib
import requests
from abc import ABC, abstractmethod
from urllib.parse import urljoin
from datetime import datetime
from shared.discord import discordUpdate
from shared.requests import retryRequest
from shared.shared import realdebrid, torbox, mediaExtensions, checkRequiredEnvs

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

    def __init__(self, f, fileData, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__()
        self.f = f
        self.fileData = fileData
        self.file = file
        self.failIfNotCached = failIfNotCached
        self.onlyLargestFile = onlyLargestFile
        self.incompatibleHashSize = False
        self.id = None
        self._info = None
        self._hash = None
        self._instantAvailability = None
    
    def print(self, *values: object):
        print(f"[{datetime.now()}] [{self.__class__.__name__}] [{self.file.fileInfo.filenameWithoutExt}]", *values)

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
    async def getInfo(self, refresh=False):
        pass

    @abstractmethod
    async def selectFiles(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    async def getTorrentPath(self):
        pass

    @abstractmethod
    def _addTorrentFile(self):
        pass

    @abstractmethod
    def _addMagnetFile(self):
        pass

    def _enforceId(self):
        if not self.id:
            raise Exception("Id is required. Must be acquired via successfully running submitTorrent() first.")

class RealDebrid(TorrentBase):
    def __init__(self, f, fileData, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__(f, fileData, file, failIfNotCached, onlyLargestFile)
        self.headers = {'Authorization': f'Bearer {realdebrid["apiKey"]}'}
        self.mountTorrentsPath = realdebrid["mountTorrentsPath"]

    def submitTorrent(self):
        if self.failIfNotCached:
            instantAvailability = self._getInstantAvailability()
            self.print('instantAvailability:', not not instantAvailability)
            if not instantAvailability:
                return False

        return not not self.addTorrent()

    def _getInstantAvailability(self, refresh=False):
        if refresh or not self._instantAvailability:
            torrentHash = self.getHash()
            self.print('hash:', torrentHash)

            if len(torrentHash) != 40 or True:
                self.incompatibleHashSize = True
                return True

            instantAvailabilityRequest = retryRequest(
                lambda: requests.get(urljoin(realdebrid['host'], f"torrents/instantAvailability/{torrentHash}"), headers=self.headers),
                print=self.print
            )
            if instantAvailabilityRequest is None:
                return None

            instantAvailabilities = instantAvailabilityRequest.json()
            self.print('instantAvailabilities:', instantAvailabilities)
            if not instantAvailabilities: return

            instantAvailabilityHosters = next(iter(instantAvailabilities.values()))
            if not instantAvailabilityHosters: return

            self._instantAvailability = next(iter(instantAvailabilityHosters.values()))

        return self._instantAvailability
    
    def _getAvailableHost(self):
        availableHostsRequest = retryRequest(
            lambda: requests.get(urljoin(realdebrid['host'], "torrents/availableHosts"), headers=self.headers),
            print=self.print
        )
        if availableHostsRequest is None:
            return None

        availableHosts = availableHostsRequest.json()
        return availableHosts[0]['host']
    
    async def getInfo(self, refresh=False):
        self._enforceId()

        if refresh or not self._info:
            infoRequest = retryRequest(
                lambda: requests.get(urljoin(realdebrid['host'], f"torrents/info/{self.id}"), headers=self.headers),
                print=self.print
            )
            if infoRequest is None:
                self._info = None
            else:
                info = infoRequest.json()
                info['status'] = self._normalize_status(info['status'])
                self._info = info

        return self._info

    async def selectFiles(self):
        self._enforceId()

        info = await self.getInfo()
        if info is None:
            return False

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
        selectFilesRequest = retryRequest(
            lambda: requests.post(urljoin(realdebrid['host'], f"torrents/selectFiles/{self.id}"), headers=self.headers, data=files),
            print=self.print
        )
        if selectFilesRequest is None:
            return False
        
        return True

    def delete(self):
        self._enforceId()

        deleteRequest = retryRequest(
            lambda: requests.delete(urljoin(realdebrid['host'], f"torrents/delete/{self.id}"), headers=self.headers),
            print=self.print
        )
        return not not deleteRequest


    async def getTorrentPath(self):
        filename = (await self.getInfo())['filename']
        originalFilename = (await self.getInfo())['original_filename']

        folderPathMountFilenameTorrent = os.path.join(self.mountTorrentsPath, filename)
        folderPathMountOriginalFilenameTorrent = os.path.join(self.mountTorrentsPath, originalFilename)
        folderPathMountOriginalFilenameWithoutExtTorrent = os.path.join(self.mountTorrentsPath, os.path.splitext(originalFilename)[0])

        if os.path.exists(folderPathMountFilenameTorrent) and os.listdir(folderPathMountFilenameTorrent):
            folderPathMountTorrent = folderPathMountFilenameTorrent
        elif os.path.exists(folderPathMountOriginalFilenameTorrent) and os.listdir(folderPathMountOriginalFilenameTorrent):
            folderPathMountTorrent = folderPathMountOriginalFilenameTorrent
        elif (originalFilename.endswith(('.mkv', '.mp4')) and
                os.path.exists(folderPathMountOriginalFilenameWithoutExtTorrent) and os.listdir(folderPathMountOriginalFilenameWithoutExtTorrent)):
            folderPathMountTorrent = folderPathMountOriginalFilenameWithoutExtTorrent
        else:
            folderPathMountTorrent = None

        return folderPathMountTorrent

    def _addFile(self, request, endpoint, data):
        host = self._getAvailableHost()
        if host is None:
            return None

        request = retryRequest(
            lambda: request(urljoin(realdebrid['host'], endpoint), params={'host': host}, headers=self.headers, data=data),
            print=self.print
        )
        if request is None:
            return None

        response = request.json()
        self.print('response info:', response)
        self.id = response['id']

        return self.id

    def _addTorrentFile(self):
        return self._addFile(requests.put, "torrents/addTorrent", self.f)

    def _addMagnetFile(self):
        return self._addFile(requests.post, "torrents/addMagnet", {'magnet': self.fileData})
    
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
    def __init__(self, f, fileData, file, failIfNotCached, onlyLargestFile) -> None:
        super().__init__(f, fileData, file, failIfNotCached, onlyLargestFile)
        self.headers = {'Authorization': f'Bearer {torbox["apiKey"]}'}
        self.mountTorrentsPath = torbox["mountTorrentsPath"]
        self.submittedTime = None
        self.lastInactiveCheck = None

        userInfoRequest = retryRequest(
            lambda: requests.get(urljoin(torbox['host'], "user/me"), headers=self.headers),
            print=self.print
        )
        if userInfoRequest is not None:
            userInfo = userInfoRequest.json()
            self.authId = userInfo['data']['auth_id']

    def submitTorrent(self):
        if self.failIfNotCached:
            instantAvailability = self._getInstantAvailability()
            self.print('instantAvailability:', not not instantAvailability)
            if not instantAvailability:
                return False
            
        if self.addTorrent():
            self.submittedTime = datetime.now()
            return True
        return False
    
    def _getInstantAvailability(self, refresh=False):
        if refresh or not self._instantAvailability:
            torrentHash = self.getHash()
            self.print('hash:', torrentHash)

            instantAvailabilityRequest = retryRequest(
                lambda: requests.get(
                    urljoin(torbox['host'], "torrents/checkcached"),
                    headers=self.headers,
                    params={'hash': torrentHash, 'format': 'object'}
                ),
                print=self.print
            )
            if instantAvailabilityRequest is None:
                return None

            instantAvailabilities = instantAvailabilityRequest.json()
            self.print('instantAvailabilities:', instantAvailabilities)
            
            # Check if 'data' exists and is not None or False
            if instantAvailabilities and 'data' in instantAvailabilities and instantAvailabilities['data']:
                self._instantAvailability = instantAvailabilities['data']
            else:
                self._instantAvailability = None
        
        return self._instantAvailability

    async def getInfo(self, refresh=False):
        self._enforceId()

        if refresh or not self._info:
            if not self.authId:
                return None
            
            currentTime = datetime.now()
            if (currentTime - self.submittedTime).total_seconds() < 300:
                if not self.lastInactiveCheck or (currentTime - self.lastInactiveCheck).total_seconds() > 5:
                    inactiveCheckUrl = f"https://relay.torbox.app/v1/inactivecheck/torrent/{self.authId}/{self.id}"
                    retryRequest(
                        lambda: requests.get(inactiveCheckUrl),
                        print=self.print
                    )
                    self.lastInactiveCheck = currentTime
            for _ in range(60):
                infoRequest = retryRequest(
                    lambda: requests.get(urljoin(torbox['host'], "torrents/mylist"), headers=self.headers),
                    print=self.print
                )
                if infoRequest is None:
                    return None

                torrents = infoRequest.json()['data']
                
                for torrent in torrents:
                    if torrent['id'] == self.id:
                        torrent['status'] = self._normalize_status(torrent['download_state'], torrent['download_finished'])
                        self._info = torrent
                        return self._info
                
                await asyncio.sleep(1)
        return self._info

    async def selectFiles(self):
        pass

    def delete(self):
        self._enforceId()

        deleteRequest = retryRequest(
            lambda: requests.delete(urljoin(torbox['host'], "torrents/controltorrent"), headers=self.headers, data={'torrent_id': self.id, 'operation': "Delete"}),
            print=self.print
        )
        return not not deleteRequest

    async def getTorrentPath(self):
        filename = (await self.getInfo())['files'][0]['name'].split("/")[0]

        folderPathMountFilenameTorrent = os.path.join(self.mountTorrentsPath, filename)
       
        if os.path.exists(folderPathMountFilenameTorrent) and os.listdir(folderPathMountFilenameTorrent):
            folderPathMountTorrent = folderPathMountFilenameTorrent
        else:
            folderPathMountTorrent = None

        return folderPathMountTorrent

    def _addFile(self, data=None, files=None):
        request = retryRequest(
            lambda: requests.post(urljoin(torbox['host'], "torrents/createtorrent"), headers=self.headers, data=data, files=files),
            print=self.print
        )
        if request is None:
            return None
        
        response = request.json()
        self.print('response info:', response)
        
        if response.get('detail') == 'queued':
            return None
        
        self.id = response['data']['torrent_id']

        return self.id

    def _addTorrentFile(self):
        nametorrent = self.f.name.split('/')[-1]
        files = {'file': (nametorrent, self.f, 'application/x-bittorrent')}
        return self._addFile(files=files)

    def _addMagnetFile(self):
        return self._addFile(data={'magnet': self.fileData})

    def _normalize_status(self, status, download_finished):
        if download_finished:
            return self.STATUS_COMPLETED
        elif status in [
            'completed', 'cached', 'paused', 'downloading', 'uploading',
            'checkingResumeData', 'metaDL', 'pausedUP', 'queuedUP', 'checkingUP',
            'forcedUP', 'allocating', 'downloading', 'metaDL', 'pausedDL',
            'queuedDL', 'checkingDL', 'forcedDL', 'checkingResumeData', 'moving'
        ]:
            return self.STATUS_DOWNLOADING
        elif status in ['error', 'stalledUP', 'stalledDL', 'stalled (no seeds)', 'missingFiles', 'failed']:
            return self.STATUS_ERROR
        return status

class Torrent(TorrentBase):
    def getHash(self):

        if not self._hash:
            import bencode3
            self._hash = hashlib.sha1(bencode3.bencode(bencode3.bdecode(self.fileData)['info'])).hexdigest()
        
        return self._hash

    def addTorrent(self):
        return self._addTorrentFile()

class Magnet(TorrentBase):
    def getHash(self):

        if not self._hash:
            # Consider changing when I'm more familiar with hashes
            self._hash = re.search('xt=urn:btih:(.+?)(?:&|$)', self.fileData).group(1)
        
        return self._hash
    
    def addTorrent(self):
        return self._addMagnetFile()


class RealDebridTorrent(RealDebrid, Torrent):
    pass

class RealDebridMagnet(RealDebrid, Magnet):
    pass

class TorboxTorrent(Torbox, Torrent):
    pass

class TorboxMagnet(Torbox, Magnet):
    pass
