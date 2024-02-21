import shutil
import time
import traceback
import hashlib
import os
import sys
import re
import requests
import asyncio
import bencode3
from datetime import datetime
# import urllib
from werkzeug.utils import cached_property
from abc import ABC, abstractmethod
from shared.discord import discordError, discordUpdate
from shared.shared import pushbullet, realdebrid, blackhole, plex, mediaExtensions
from shared.arr import Arr, Radarr, Sonarr

rdHost = realdebrid['host']
authToken = realdebrid['apiKey']

_print = print

def print(*values: object):
    _print(f"[{datetime.now()}]", *values)


class TorrentFileInfo():
    class FileInfo():
        def __init__(self, filename, filenameWithoutExt, filePath, filePathProcessing, folderPathCompleted, folderPathMountTorrent) -> None:
            self.filename = filename
            self.filenameWithoutExt = filenameWithoutExt
            self.filePath = filePath
            self.filePathProcessing = filePathProcessing
            self.folderPathCompleted = folderPathCompleted
            self.folderPathMountTorrent = folderPathMountTorrent

    class TorrentInfo():
        def __init__(self, isTorrentOrMagnet, isDotTorrentFile) -> None:
            self.isTorrentOrMagnet = isTorrentOrMagnet
            self.isDotTorrentFile = isDotTorrentFile

    def __init__(self, filename, isRadarr) -> None:
        print('filename:', filename)
        baseBath = getPath(isRadarr)
        isDotTorrentFile = filename.casefold().endswith('.torrent')
        isTorrentOrMagnet = isDotTorrentFile or filename.casefold().endswith('.magnet')
        filenameWithoutExt, _ = os.path.splitext(filename)
        filePath = os.path.join(baseBath, filename)
        filePathProcessing = os.path.join(baseBath, 'processing', filename)
        folderPathCompleted = os.path.join(baseBath, 'completed', filenameWithoutExt)
        folderPathMountTorrent = os.path.join(blackhole['rdMountTorrentsPath'], filenameWithoutExt)
        
        self.fileInfo = self.FileInfo(filename, filenameWithoutExt, filePath, filePathProcessing, folderPathCompleted, folderPathMountTorrent)
        self.torrentInfo = self.TorrentInfo(isTorrentOrMagnet, isDotTorrentFile)
        

class TorrentBase(ABC):
    def __init__(self, f, file, fail, failIfNotCached, onlyLargestFile) -> None:
        super().__init__()
        self.f = f
        self.file = file
        self.fail = fail
        self.failIfNotCached = failIfNotCached
        self.onlyLargestFile = onlyLargestFile
        self.id = None
        self._info = None
        self._instantAvailability = None
        self._hash = None
        self.incompatibleHashSize = False
    
    def print(self, *values: object):
            print(f"[{self.file.fileInfo.filenameWithoutExt}]", *values)

    @cached_property
    def fileData(self):
        fileData = self.f.read()
        self.f.seek(0)

        return fileData


    def submitTorrent(self):
        if self.failIfNotCached:
            instantAvailability = self.getInstantAvailability()
            self.print('instantAvailability:', not not instantAvailability)
            if not instantAvailability:
                self.fail(self)
                return False

        availableHost = self.getAvailableHost()
        self.addTorrent(availableHost)
        return True

    @abstractmethod
    def getHash(self):
        pass
    
    @abstractmethod
    def addTorrent(self, host):
        pass

    def getInstantAvailability(self, refresh=False):
        if refresh or not self._instantAvailability:
            torrentHash = self.getHash()
            self.print('hash:', torrentHash)

            if len(torrentHash) != 40:
                self.incompatibleHashSize = True
                return True

            instantAvailabilityRequest = requests.get(f"{rdHost}torrents/instantAvailability/{torrentHash}?auth_token={authToken}")
            instantAvailabilities = instantAvailabilityRequest.json()
            self.print('instantAvailabilities:', instantAvailabilities)
            instantAvailabilityHosters = next(iter(instantAvailabilities.values()))
            if not instantAvailabilityHosters: return

            self._instantAvailability = next(iter(instantAvailabilityHosters.values()))

        return self._instantAvailability
    
    def getAvailableHost(self):
        availableHostsRequest = requests.get(f"{rdHost}torrents/availableHosts?auth_token={authToken}")
        availableHosts = availableHostsRequest.json()

        return availableHosts[0]['host']
    
    def getInfo(self, refresh=False):
        self._enforceId()

        if refresh or not self._info:
            infoRequest = requests.get(f"{rdHost}torrents/info/{self.id}?auth_token={authToken}")
            self._info = infoRequest.json()

        return self._info

    def selectFiles(self):
        self._enforceId()

        info = self.getInfo()
        self.print('files:', info['files'])
        mediaFiles = [file for file in info['files'] if os.path.splitext(file['path'])[1] in mediaExtensions]
        mediaFileIds = {str(file['id']) for file in mediaFiles}
        self.print('required fileIds:', mediaFileIds)
        
        largestMediaFile = max(mediaFiles, key=lambda file: file['bytes'])
        largestMediaFileId = str(largestMediaFile['id'])
        self.print('only largest file:', self.onlyLargestFile)
        self.print('largest file:', largestMediaFile)
        if self.onlyLargestFile and len(mediaFiles) > 1:
            discordUpdate('largest file:', largestMediaFile['path'])

        if self.failIfNotCached and not self.incompatibleHashSize:
            targetFileIds = {largestMediaFileId} if self.onlyLargestFile else mediaFileIds
            if not any(set(fileGroup.keys()) == targetFileIds for fileGroup in self._instantAvailability):
                extraFilesGroup = next(fileGroup for fileGroup in self._instantAvailability if largestMediaFileId in fileGroup.keys())
                if self.onlyLargestFile and extraFilesGroup:
                    self.print('extra files required for cache:', extraFilesGroup)
                    discordUpdate('Extra files required for cache:', extraFilesGroup)
                return False
                
        files = {'files': [largestMediaFileId] if self.onlyLargestFile else ','.join(mediaFileIds)}
        selectFilesRequest = requests.post(f"{rdHost}torrents/selectFiles/{self.id}?auth_token={authToken}", data=files)
        
        return True

    def delete(self):
        self._enforceId()

        deleteRequest = requests.delete(f"{rdHost}torrents/delete/{self.id}?auth_token={authToken}")


    def _enforceId(self):
        if not self.id: raise Exception("Id is required. Must be aquired via sucessfully running submitTorrent() first.")


class Torrent(TorrentBase):
    def getHash(self):

        if not self._hash:
            self._hash = hashlib.sha1(bencode3.bencode(bencode3.bdecode(self.fileData)['info'])).hexdigest()
        
        return self._hash

    def addTorrent(self, host):
        addTorrentRequest = requests.put(f"{rdHost}torrents/addTorrent?host={host}&auth_token={authToken}", data=self.f)
        addTorrentResponse = addTorrentRequest.json()
        self.print('torrent info:', addTorrentResponse)
        
        self.id = addTorrentResponse['id']
        return self.id


class Magnet(TorrentBase):
    def getHash(self):

        if not self._hash:
            # Consider changing when I'm more familiar with hashes
            self._hash = re.search('xt=urn:btih:(.+?)(?:&|$)', self.fileData).group(1)
        
        return self._hash
    
    def addTorrent(self, host):
        addMagnetRequest = requests.post(f"{rdHost}torrents/addMagnet?host={host}&auth_token={authToken}", data={'magnet': self.fileData})
        addMagnetResponse = addMagnetRequest.json()
        self.print('magnet info:', addMagnetResponse)
        
        self.id = addMagnetResponse['id']

        return self.id

def getPath(isRadarr):
    return os.path.join(blackhole['baseWatchPath'], blackhole['radarrPath'] if isRadarr else blackhole['sonarrPath'])

# From Radarr Radarr/src/NzbDrone.Core/Organizer/FileNameBuilder.cs
def cleanFileName(name):
    result = name
    badCharacters = ["\\", "/", "<", ">", "?", "*", ":", "|", "\""]
    goodCharacters = ["+", "+", "", "", "!", "-", "", "", ""]

    for i, char in enumerate(badCharacters):
        result = result.replace(char, goodCharacters[i])
    
    return result.strip()


def copyFiles(file: TorrentFileInfo, folderPathMountTorrent, arr: Arr):
    # Consider removing this and always streaming
    try:
        _print = globals()['print']

        def print(*values: object):
            _print(f"[{file.fileInfo.filenameWithoutExt}]", *values)

        count = 0
        print('Waiting for arr to delete folders...')
        while True:
            count += 1
            if not os.path.exists(file.fileInfo.folderPathCompleted):
                print('Deleted')
                print('Copying actual files to arr folder...')
                shutil.copytree(folderPathMountTorrent, file.fileInfo.folderPathCompleted)
                arr.refreshMonitoredDownloads()   
                print('Copied')          
                break
            time.sleep(1)
            if count == 180:
                print('copyCount > 180')
                discordError(f"{file.fileInfo.filenameWithoutExt} copy attempt acount > 180", "Shortcut has not finished importing yet")

    except:
        e = traceback.format_exc()

        print(f"Error copying files for {file.fileInfo.filenameWithoutExt}")
        print(e)

        discordError(f"Error copying files for {file.fileInfo.filenameWithoutExt}", e)

import signal

async def processFile(file: TorrentFileInfo, arr: Arr, isRadarr):
    try:
        _print = globals()['print']

        def print(*values: object):
            _print(f"[{file.fileInfo.filenameWithoutExt}]", *values)

        from concurrent.futures import ThreadPoolExecutor

        def read_file(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                f.read(1)

        async def is_accessible(path, timeout=10):
            with ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                try:
                    await asyncio.wait_for(loop.run_in_executor(executor, read_file, path), timeout=timeout)
                    discordUpdate('good')
                    return True
                except Exception as e:
                    discordError('error', e)
                    return False
                finally:
                    executor.shutdown(wait=False)

        with open(file.fileInfo.filePathProcessing, 'rb' if file.torrentInfo.isDotTorrentFile else 'r') as f:
            def fail(torrent: TorrentBase, arr: Arr=arr):
                print(f"Failed")

                history = arr.getHistory(blackhole['historyPageSize'])['records']
                items = (item for item in history if item['data'].get('torrentInfoHash', '').casefold() == torrent.getHash().casefold() or cleanFileName(item['sourceTitle'].casefold()) == torrent.file.fileInfo.filenameWithoutExt.casefold())
                
                if not items:
                    raise Exception("No history items found to cancel")
                
                for item in items:
                    # TODO: See if we can fail without blacklisting as cached items constantly changes
                    arr.failHistoryItem(item['id'])

            onlyLargestFile = isRadarr or bool(re.search(r'S[\d]{2}E[\d]{2}', file.fileInfo.filename))
            if file.torrentInfo.isDotTorrentFile:
                torrent = Torrent(f, file, fail, blackhole['failIfNotCached'], onlyLargestFile)
            else:
                torrent = Magnet(f, file, fail, blackhole['failIfNotCached'], onlyLargestFile)
            
            if torrent.submitTorrent():
                count = 0
                while True:
                    count += 1
                    info = torrent.getInfo(refresh=True)
                    status = info['status']
                    print('status:', status)

                    if status == 'waiting_files_selection':
                        if not torrent.selectFiles():
                            torrent.delete()
                            fail(torrent)
                            break
                    elif status == 'magnet_conversion' or status == 'queued' or status == 'downloading' or status == 'compressing' or status == 'uploading':
                        # Send progress to arr
                        progress = info['progress']
                        print(progress)
                        if torrent.incompatibleHashSize:
                            print("Non-cached incompatible hash sized torrent")
                            torrent.delete()
                            fail(torrent)
                            break
                        await asyncio.sleep(1)
                    elif status == 'magnet_error' or status == 'error' or status == 'dead' or status == 'virus':
                        fail(torrent)
                        break
                    elif status == 'downloaded':
                        existsCount = 0
                        print('Waiting for folders to refresh...')
                        while existsCount <= blackhole['waitForTorrentTimeout']:
                            existsCount += 1
                            folderPathMountTorrent = os.path.join(blackhole['rdMountTorrentsPath'], info['filename'])
                            if os.path.exists(folderPathMountTorrent) and os.listdir(folderPathMountTorrent):
                                multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
                                multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
                                multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'

                                multiSeasonMatch = re.search(multiSeasonRegexCombined, file.fileInfo.filenameWithoutExt)

                                for root, dirs, files in os.walk(folderPathMountTorrent):
                                    relRoot = os.path.relpath(root, folderPathMountTorrent)
                                    for filename in files:
                                        # Check if the file is accessible
                                        # if not await is_accessible(os.path.join(root, filename)):
                                        #     print(f"Timeout reached when accessing file: {filename}")
                                        #     discordError(f"Timeout reached when accessing file", filename)
                                            # Uncomment the following line to fail the entire torrent if the timeout on any of its files are reached
                                            # fail(torrent)
                                            # return
                                        
                                        if multiSeasonMatch:
                                            seasonMatch = re.search(r'S([\d]{2})E[\d]{2}', filename)
                                            
                                            if seasonMatch:
                                                season = seasonMatch.group(1)
                                                seasonShort = season[1:] if season[0] == '0' else season

                                                seasonFolderPathCompleted = re.sub(multiSeasonRegex1, seasonShort, file.fileInfo.folderPathCompleted)
                                                seasonFolderPathCompleted = re.sub(multiSeasonRegex2, season, seasonFolderPathCompleted)

                                                os.makedirs(os.path.join(seasonFolderPathCompleted, relRoot), exist_ok=True)
                                                os.symlink(os.path.join(root, filename), os.path.join(seasonFolderPathCompleted, relRoot, filename))
                                                print('Season Recursive:', f"{os.path.join(seasonFolderPathCompleted, relRoot, filename)} -> {os.path.join(root, filename)}")
                                                # refreshEndpoint = f"{plex['serverHost']}/library/sections/{plex['serverMovieLibraryId'] if isRadarr else plex['serverTvShowLibraryId']}/refresh?path={urllib.parse.quote_plus(os.path.join(seasonFolderPathCompleted, relRoot))}&X-Plex-Token={plex['serverApiKey']}"
                                                # cancelRefreshRequest = requests.delete(refreshEndpoint, headers={'Accept': 'application/json'})
                                                # refreshRequest = requests.get(refreshEndpoint, headers={'Accept': 'application/json'})

                                                continue


                                        os.makedirs(os.path.join(file.fileInfo.folderPathCompleted, relRoot), exist_ok=True)
                                        os.symlink(os.path.join(root, filename), os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename))
                                        print('Recursive:', f"{os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)} -> {os.path.join(root, filename)}")
                                        # refreshEndpoint = f"{plex['serverHost']}/library/sections/{plex['serverMovieLibraryId'] if isRadarr else plex['serverTvShowLibraryId']}/refresh?path={urllib.parse.quote_plus(os.path.join(file.fileInfo.folderPathCompleted, relRoot))}&X-Plex-Token={plex['serverApiKey']}"
                                        # cancelRefreshRequest = requests.delete(refreshEndpoint, headers={'Accept': 'application/json'})
                                        # refreshRequest = requests.get(refreshEndpoint, headers={'Accept': 'application/json'})
                                
                                # refreshEndpoint = f"{plex['serverHost']}/library/sections/{plex['serverMovieLibraryId'] if isRadarr else plex['serverTvShowLibraryId']}/refresh?X-Plex-Token={plex['serverApiKey']}"
                                # cancelRefreshRequest = requests.delete(refreshEndpoint, headers={'Accept': 'application/json'})
                                # refreshRequest = requests.get(refreshEndpoint, headers={'Accept': 'application/json'})
                                arr.refreshMonitoredDownloads()

                                print('Refreshed')
                                discordUpdate(f"Sucessfully processed {file.fileInfo.filenameWithoutExt}", f"Now available for immediate consumption! existsCount: {existsCount}")
                                
                                # await asyncio.get_running_loop().run_in_executor(None, copyFiles, file, folderPathMountTorrent, arr)
                                break
                            
                            if existsCount == blackhole['rdMountRefreshSeconds'] + 1:
                                print(f"Torrent folder not found in filesystem: {file.fileInfo.filenameWithoutExt}")
                                discordError("Torrent folder not found in filesystem", file.fileInfo.filenameWithoutExt)

                            await asyncio.sleep(1)
                        break
                
                    if count == 21:
                        print('infoCount > 20')
                        discordError(f"{file.fileInfo.filenameWithoutExt} info attempt count > 20", status)
                    elif count == blackhole['waitForTorrentTimeout']:
                        print('infoCount == 60 - Failing')
                        fail(torrent)
                        break

            os.remove(file.fileInfo.filePathProcessing)
    except:
        e = traceback.format_exc()

        print(f"Error processing {file.fileInfo.filenameWithoutExt}")
        print(e)

        discordError(f"Error processing {file.fileInfo.filenameWithoutExt}", e)

def getFiles(isRadarr):
    print('getFiles')
    files = (TorrentFileInfo(filename, isRadarr) for filename in os.listdir(getPath(isRadarr)) if filename not in ['processing', 'completed'])
    return [file for file in files if file.torrentInfo.isTorrentOrMagnet]

async def on_created():
    print("Enter 'on_created'")
    try:
        print('radarr/sonarr:', sys.argv[1])

        isRadarr = sys.argv[1] == 'radarr'

        if isRadarr:
            arr = Radarr()
        else:
            arr = Sonarr()

        futures: list[asyncio.Future] = []
        firstGo = True
        
        # Consider switching to a queue
        while firstGo or not all(future.done() for future in futures):
            files = getFiles(isRadarr)
            if files:
                for file in files:
                    os.renames(file.fileInfo.filePath, file.fileInfo.filePathProcessing)
                futures.append(asyncio.gather(*(processFile(file, arr, isRadarr) for file in files)))
            elif firstGo:
                print('No torrent files found')
            firstGo = False
            await asyncio.sleep(1)

        await asyncio.gather(*futures)
    except:
        e = traceback.format_exc()

        print(f"Error processing")
        print(e)

        discordError(f"Error processing", e)
    print("Exit 'on_created'")

asyncio.run(on_created())
