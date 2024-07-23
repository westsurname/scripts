import shutil
import time
import traceback
import os
import sys
import re
import requests
import asyncio
import uuid
from datetime import datetime
# import urllib
from shared.discord import discordError, discordUpdate
from shared.shared import realdebrid, torbox, blackhole, plex, checkRequiredEnvs
from shared.arr import Arr, Radarr, Sonarr
from shared.debrid import TorrentBase, RealDebridTorrent, RealDebridMagnet, TorboxTorrent, TorboxMagnet

_print = print

def print(*values: object):
    _print(f"[{datetime.now()}]", *values)

requiredEnvs = {
    'Blackhole base watch path': (blackhole['baseWatchPath'],),
    'Blackhole Radarr path': (blackhole['radarrPath'],),
    'Blackhole Sonarr path': (blackhole['sonarrPath'],),
    'Blackhole fail if not cached': (blackhole['failIfNotCached'],),
    'Blackhole RD mount refresh seconds': (blackhole['rdMountRefreshSeconds'],),
    'Blackhole wait for torrent timeout': (blackhole['waitForTorrentTimeout'],),
    'Blackhole history page size': (blackhole['historyPageSize'],)
}

checkRequiredEnvs(requiredEnvs)

class TorrentFileInfo():
    class FileInfo():
        def __init__(self, filename, filenameWithoutExt, filePath, filePathProcessing, folderPathCompleted) -> None:
            self.filename = filename
            self.filenameWithoutExt = filenameWithoutExt
            self.filePath = filePath
            self.filePathProcessing = filePathProcessing
            self.folderPathCompleted = folderPathCompleted

    class TorrentInfo():
        def __init__(self, isTorrentOrMagnet, isDotTorrentFile) -> None:
            self.isTorrentOrMagnet = isTorrentOrMagnet
            self.isDotTorrentFile = isDotTorrentFile

    def __init__(self, filename, isRadarr) -> None:
        print('filename:', filename)
        baseBath = getPath(isRadarr)
        uniqueId = str(uuid.uuid4())[:8]  # Generate a unique identifier
        isDotTorrentFile = filename.casefold().endswith('.torrent')
        isTorrentOrMagnet = isDotTorrentFile or filename.casefold().endswith('.magnet')
        filenameWithoutExt, ext = os.path.splitext(filename)
        filePath = os.path.join(baseBath, filename)
        filePathProcessing = os.path.join(baseBath, 'processing', f"{filenameWithoutExt}_{uniqueId}{ext}")
        folderPathCompleted = os.path.join(baseBath, 'completed', filenameWithoutExt)
        
        self.fileInfo = self.FileInfo(filename, filenameWithoutExt, filePath, filePathProcessing, folderPathCompleted)
        self.torrentInfo = self.TorrentInfo(isTorrentOrMagnet, isDotTorrentFile)

def getPath(isRadarr, create=False):
    baseWatchPath = blackhole['baseWatchPath']
    absoluteBaseWatchPath = baseWatchPath if os.path.isabs(baseWatchPath) else os.path.abspath(baseWatchPath)
    finalPath = os.path.join(absoluteBaseWatchPath, blackhole['radarrPath'] if isRadarr else blackhole['sonarrPath'])

    if create:
        for sub_path in ['', 'processing', 'completed']:
            path_to_check = os.path.join(finalPath, sub_path)
            if not os.path.exists(path_to_check):
                os.makedirs(path_to_check)
        
    return finalPath

# From Radarr Radarr/src/NzbDrone.Core/Organizer/FileNameBuilder.cs
def cleanFileName(name):
    result = name
    badCharacters = ["\\", "/", "<", ">", "?", "*", ":", "|", "\""]
    goodCharacters = ["+", "+", "", "", "!", "-", "", "", ""]

    for i, char in enumerate(badCharacters):
        result = result.replace(char, goodCharacters[i])
    
    return result.strip()

refreshingTask = None

async def refreshArr(arr: Arr, count=60):
    # TODO: Change to refresh until found/imported
    async def refresh():
        for _ in range(count):
            arr.refreshMonitoredDownloads()
            await asyncio.sleep(1)

    global refreshingTask
    if refreshingTask and not refreshingTask.done():
        print("Refresh already in progress, restarting...")
        refreshingTask.cancel()

    refreshingTask = asyncio.create_task(refresh())
    try:
        await refreshingTask
    except asyncio.CancelledError:
        pass

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

async def processTorrent(torrent: TorrentBase, file: TorrentFileInfo, arr: Arr) -> bool:
    _print = globals()['print']

    def print(*values: object):
        _print(f"[{torrent.__class__.__name__}] [{file.fileInfo.filenameWithoutExt}]", *values)
        
    if not torrent.submitTorrent():
        return False

    count = 0
    while True:
        count += 1
        info = await torrent.getInfo(refresh=True)
        if not info:
            return False

        status = info['status']
        
        print('status:', status)

        if status == torrent.STATUS_WAITING_FILES_SELECTION:
            if not await torrent.selectFiles():
                torrent.delete()
                return False
        elif status == torrent.STATUS_DOWNLOADING:
            # Send progress to arr
            progress = info['progress']
            print(f"Progress: {progress:.2f}%")
            if torrent.incompatibleHashSize and torrent.failIfNotCached:
                print("Non-cached incompatible hash sized torrent")
                torrent.delete()
                return False
            await asyncio.sleep(1)
        elif status == torrent.STATUS_ERROR:
            return False
        elif status == torrent.STATUS_COMPLETED:
            existsCount = 0
            print('Waiting for folders to refresh...')

            while True:
                existsCount += 1
                
                folderPathMountTorrent = await torrent.getTorrentPath()
                if folderPathMountTorrent:
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
                    
                    print('Refreshed')
                    discordUpdate(f"Sucessfully processed {file.fileInfo.filenameWithoutExt}", f"Now available for immediate consumption! existsCount: {existsCount}")
                    
                    # refreshEndpoint = f"{plex['serverHost']}/library/sections/{plex['serverMovieLibraryId'] if isRadarr else plex['serverTvShowLibraryId']}/refresh?X-Plex-Token={plex['serverApiKey']}"
                    # cancelRefreshRequest = requests.delete(refreshEndpoint, headers={'Accept': 'application/json'})
                    # refreshRequest = requests.get(refreshEndpoint, headers={'Accept': 'application/json'})
                    await refreshArr(arr)

                    # await asyncio.get_running_loop().run_in_executor(None, copyFiles, file, folderPathMountTorrent, arr)
                    return True
                
                if existsCount >= blackhole['rdMountRefreshSeconds'] + 1:
                    print(f"Torrent folder not found in filesystem: {file.fileInfo.filenameWithoutExt}")
                    discordError("Torrent folder not found in filesystem", file.fileInfo.filenameWithoutExt)

                    return False

                await asyncio.sleep(1)
    
        if torrent.failIfNotCached and count >= blackhole['waitForTorrentTimeout']:
            print(f"Torrent timeout: {file.fileInfo.filenameWithoutExt} - {status}")
            discordError("Torrent timeout", f"{file.fileInfo.filenameWithoutExt} - {status}")

            return False

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

        time.sleep(.1) # Wait before processing the file in case it isn't fully written yet.
        os.renames(file.fileInfo.filePath, file.fileInfo.filePathProcessing)

        with open(file.fileInfo.filePathProcessing, 'rb' if file.torrentInfo.isDotTorrentFile else 'r') as f:
            fileData = f.read()
            f.seek(0)
            
            torrentConstructors = []
            if realdebrid['enabled']:
                torrentConstructors.append(RealDebridTorrent if file.torrentInfo.isDotTorrentFile else RealDebridMagnet)
            if torbox['enabled']:
                torrentConstructors.append(TorboxTorrent if file.torrentInfo.isDotTorrentFile else TorboxMagnet)

            onlyLargestFile = isRadarr or bool(re.search(r'S[\d]{2}E[\d]{2}(?![\W_][\d]{2}[\W_])', file.fileInfo.filename))
            if not blackhole['failIfNotCached']:
                torrents = [constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile) for constructor in torrentConstructors]
                results = await asyncio.gather(*(processTorrent(torrent, file, arr) for torrent in torrents))
                
                if not any(results):
                    await asyncio.gather(*(fail(torrent, arr) for torrent in torrents))
            else:
                for i, constructor in enumerate(torrentConstructors):
                    isLast = (i == len(torrentConstructors) - 1)
                    torrent = constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile)

                    if await processTorrent(torrent, file, arr):
                        break
                    elif isLast:
                        await fail(torrent, arr)

            os.remove(file.fileInfo.filePathProcessing)
    except:
        e = traceback.format_exc()

        print(f"Error processing {file.fileInfo.filenameWithoutExt}")
        print(e)

        discordError(f"Error processing {file.fileInfo.filenameWithoutExt}", e)

async def fail(torrent: TorrentBase, arr: Arr):
    _print = globals()['print']

    def print(*values: object):
        _print(f"[{torrent.__class__.__name__}] [{torrent.file.fileInfo.filenameWithoutExt}]", *values)

    print(f"Failing")
    
    torrentHash = torrent.getHash()
    history = await asyncio.to_thread(arr.getHistory, blackhole['historyPageSize'])
    items = [item for item in history if (item.torrentInfoHash and item.torrentInfoHash.casefold() == torrentHash.casefold()) or cleanFileName(item.sourceTitle.casefold()) == torrent.file.fileInfo.filenameWithoutExt.casefold()]
    if not items:
        message = "No history items found to mark as failed. Arr will not attempt to grab an alternative."
        print(message)
        discordError(message, torrent.file.fileInfo.filenameWithoutExt)
    else:
        # TODO: See if we can fail without blacklisting as cached items constantly changes
        failTasks = [asyncio.to_thread(arr.failHistoryItem, item.id) for item in items]
        await asyncio.gather(*failTasks)
    print(f"Failed")
    
def getFiles(isRadarr):
    print('getFiles')
    files = (TorrentFileInfo(filename, isRadarr) for filename in os.listdir(getPath(isRadarr)) if filename not in ['processing', 'completed'])
    return [file for file in files if file.torrentInfo.isTorrentOrMagnet]

async def on_created(isRadarr):
    print("Enter 'on_created'")
    try:
        print('radarr/sonarr:', 'radarr' if isRadarr else 'sonarr')

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

if __name__ == "__main__":
    asyncio.run(on_created(isRadarr=sys.argv[1] == 'radarr'))
