import shutil
import time
import traceback
import os
import sys
import re
import requests
import asyncio
from datetime import datetime
from shared.discord import discordError, discordUpdate
from shared.shared import realdebrid, torbox, blackhole, plex, checkRequiredEnvs
from shared.arr import Arr, Radarr, Sonarr
from shared.debrid import TorrentBase, RealDebridTorrent, RealDebridMagnet, TorboxTorrent, TorboxMagnet
from RTN import parse

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
        isDotTorrentFile = filename.casefold().endswith('.torrent')
        isTorrentOrMagnet = isDotTorrentFile or filename.casefold().endswith('.magnet')
        filenameWithoutExt, _ = os.path.splitext(filename)
        filePath = os.path.join(baseBath, filename)
        filePathProcessing = os.path.join(baseBath, 'processing', filename)
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

async def refreshArr(arr: Arr, count=3, delay=10):
    for _ in range(count):
        arr.refreshMonitoredDownloads()
        await asyncio.sleep(delay)

def retryRequest(func, retries=3, delay=2, print=print):
    for attempt in range(retries):
        try:
            time.sleep(delay)  # Add delay before each API call
            response = func()
            if response.status_code == 429:  # Too Many Requests
                print(f"Rate limited, sleeping for {delay} seconds...")
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt + 1 == retries:
                return None

def copyFiles(file: TorrentFileInfo, folderPathMountTorrent, arr: Arr):
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
                discordError(f"{file.fileInfo.filenameWithoutExt} copy attempt count > 180", "Shortcut has not finished importing yet")

    except:
        e = traceback.format_exc()

        print(f"Error copying files for {file.fileInfo.filenameWithoutExt}")
        print(e)

        discordError(f"Error copying files for {file.fileInfo.filenameWithoutExt}", e)

import signal

async def processTorrent(torrent: TorrentBase, file: TorrentFileInfo, arr: Arr, message_id, parsed_title, file_info, is_movie, debrid_provider, discord_user_tag, tag_on_success) -> bool:
    _print = globals()['print']

    def print(*values: object):
        _print(f"[{torrent.__class__.__name__}] [{file.fileInfo.filenameWithoutExt}]", *values)

    color = 3447003 if not is_movie else 16776960  # Blue for show, Yellow for movie

    update_message = lambda status: discordUpdate(
        title=f"Processing {'Movie' if is_movie else 'Series'}: {parsed_title}",
        message=f"**Debrid Provider:** {debrid_provider}\n{file_info}\n**STATUS:**\n📁 Torrent Cached: {status['cached']}\n📥 Added to Debrid: {status['added']}\n🔎 Found on Mount: {status['mounted']}\n🔗 Symlinked: {status['symlinked']}",
        color=color,
        message_id=message_id,
    )

    status = {
        "cached": "⛔",
        "added": "⛔",
        "mounted": "⛔",
        "symlinked": "⛔"
    }
    
    update_message(status)

    if not torrent.submitTorrent():
        return False

    status["cached"] = "✅"
    update_message(status)

    count = 0
    while True:
        count += 1
        info = await torrent.getInfo(refresh=True)
        if not info:
            return False

        torrent_status = info['status']
        
        print('status:', torrent_status)

        if torrent_status == torrent.STATUS_WAITING_FILES_SELECTION:
            if not await torrent.selectFiles():
                torrent.delete()
                return False
            await asyncio.sleep(15)  # Add a 15-second wait between select file calls
        elif torrent_status == torrent.STATUS_DOWNLOADING:
            # Send progress to arr
            progress = info['progress']
            print(f"Progress: {progress:.2f}%")
            if torrent.incompatibleHashSize and torrent.failIfNotCached:
                print("Non-cached incompatible hash sized torrent")
                torrent.delete()
                return False
            await asyncio.sleep(1)
        elif torrent_status == torrent.STATUS_ERROR:
            return False
        elif torrent_status == torrent.STATUS_COMPLETED:
            status["added"] = "✅"
            update_message(status)
            
            existsCount = 0
            print('Waiting for folders to refresh...')

            while True:
                existsCount += 1
                
                folderPathMountTorrent = await torrent.getTorrentPath()
                if folderPathMountTorrent:
                    status["mounted"] = "✅"
                    update_message(status)

                    multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
                    multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
                    multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'

                    multiSeasonMatch = re.search(multiSeasonRegexCombined, file.fileInfo.filenameWithoutExt)

                    for root, dirs, files in os.walk(folderPathMountTorrent):
                        relRoot = os.path.relpath(root, folderPathMountTorrent)
                        for filename in files:
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
                                    continue

                            os.makedirs(os.path.join(file.fileInfo.folderPathCompleted, relRoot), exist_ok=True)
                            os.symlink(os.path.join(root, filename), os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename))
                            print('Recursive:', f"{os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)} -> {os.path.join(root, filename)}")
                    
                    status["symlinked"] = "✅"
                    update_message(status)

                    print('Refreshed')

                    # Refresh arrs every 10 seconds for the first 30 seconds
                    await refreshArr(arr, count=3, delay=10)

                    # Check for the existence of the symlink every 5 seconds
                    check_count = 0
                    while check_count < 6:
                        check_count += 1
                        arr.refreshMonitoredDownloads()
                        if not os.path.exists(os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)):
                            break
                        await asyncio.sleep(5)

                    timestamp = datetime.utcnow().isoformat() + "Z"
                    if check_count < 6:
                        discordUpdate(
                            content=discord_user_tag if tag_on_success else None,
                            title=f"Successfully Processed: {parsed_title}",
                            message=f"**Debrid Provider:** {debrid_provider}\n{file_info}\n**STATUS:**\n📁 Torrent Cached: {status['cached']}\n📥 Added to Debrid: {status['added']}\n🔎 Found on Mount: {status['mounted']}\n🔗 Symlinked: {status['symlinked']}\n✨ Successfully Processed: ✅",
                            color=65280,  # Green for success
                            message_id=message_id,
                            timestamp=timestamp
                        )
                    else:
                        discordUpdate(
                            content=discord_user_tag if tag_on_success else None,
                            title=f"Successfully Processed: {parsed_title}",
                            message=f"**Debrid Provider:** {debrid_provider}\n{file_info}\n**STATUS:**\n📁 Torrent Cached: {status['cached']}\n📥 Added to Debrid: {status['added']}\n🔎 Found on Mount: {status['mounted']}\n🔗 Symlinked: {status['symlinked']}\n✨ Successfully Processed: ✅",
                            color=65280,  # Green for success
                            message_id=message_id,
                            timestamp=timestamp
                        )

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

            # Parse torrent name using RTN
            parsed_data = parse(file.fileInfo.filename)
            parsed_title = parsed_data.parsed_title or file.fileInfo.filenameWithoutExt
            print(f"Parsed title: {parsed_title}")
            
            is_movie = parsed_data.type == "movie"
            color = 16776960 if is_movie else 3447003

            # Construct file info message
            file_info = f"**Torrent Name:** {file.fileInfo.filename}\n"
            file_info += f"**File Type:** {'Movie' if is_movie else 'Series'}\n"
            if parsed_data.year != 0:
                file_info += f"**Year:** {parsed_data.year}\n"
            file_info += f"**Resolution:** {'/'.join(parsed_data.resolution)}\n"
            file_info += f"**Codec:** {'/'.join(parsed_data.codec)}\n"
            if not is_movie:
                file_info += f"**Season:** {', '.join(map(str, parsed_data.season))}\n"
                if parsed_data.episode:
                    file_info += f"**Episode:** {', '.join(map(str, parsed_data.episode))}\n"

            torrentConstructors = []
            if realdebrid['enabled']:
                torrentConstructors.append(RealDebridTorrent if file.torrentInfo.isDotTorrentFile else RealDebridMagnet)
                debrid_provider = "Real-Debrid"
            if torbox['enabled']:
                torrentConstructors.append(TorboxTorrent if file.torrentInfo.isDotTorrentFile else TorboxMagnet)
                debrid_provider = "Torbox"

            onlyLargestFile = isRadarr or bool(re.search(r'S[\d]{2}E[\d]{2}', file.fileInfo.filename))

            # Send initial notification
            discord_user = os.getenv('DISCORD_USER_TAG')
            discord_user_tag = f"<@{discord_user}>"
            tag_on_success = os.getenv('TAG_ON_SUCCESS', 'true').lower() == 'true'
            tag_on_failure = os.getenv('TAG_ON_FAILURE', 'true').lower() == 'true'
            message_id = discordUpdate(
                title=f"Processing Torrent: {parsed_title}",
                message=f"**Debrid Provider:** {debrid_provider}\n{file_info}\n**STATUS:**\n📁 Torrent Cached: ⛔\n📥 Added to Debrid: ⛔\n🔎 Found on Mount: ⛔\n🔗 Symlinked: ⛔",
                color=color,
            )

            if not blackhole['failIfNotCached']:
                torrents = [constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile) for constructor in torrentConstructors]
                results = await asyncio.gather(*(processTorrent(torrent, file, arr, message_id, parsed_title, file_info, is_movie, debrid_provider, discord_user_tag, tag_on_success) for torrent in torrents))
                
                if not any(results):
                    for torrent in torrents:
                        fail(torrent, arr, message_id, file_info, parsed_title, is_movie, color, discord_user_tag, debrid_provider, tag_on_failure)
            else:
                for i, constructor in enumerate(torrentConstructors):
                    isLast = (i == len(torrentConstructors) - 1)
                    torrent = constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile)

                    if await processTorrent(torrent, file, arr, message_id, parsed_title, file_info, is_movie, debrid_provider, discord_user_tag, tag_on_success):
                        break
                    elif isLast:
                        fail(torrent, arr, message_id, file_info, parsed_title, is_movie, color, discord_user_tag, debrid_provider, tag_on_failure)

            os.remove(file.fileInfo.filePathProcessing)
    except:
        e = traceback.format_exc()

        print(f"Error processing {file.fileInfo.filenameWithoutExt}")
        print(e)

        discordError(f"Error processing {file.fileInfo.filenameWithoutExt}", f"Error:\n```{e}```")

def fail(torrent: TorrentBase, arr: Arr, message_id, file_info, parsed_title, is_movie, color, discord_user_tag, debrid_provider, tag_on_failure):
    _print = globals()['print']

    def print(*values: object):
        _print(f"[{torrent.__class__.__name__}] [{torrent.file.fileInfo.filenameWithoutExt}]", *values)

    print(f"Failing")
    
    torrentHash = torrent.getHash()
    history = arr.getHistory(blackhole['historyPageSize'])['records']
    items = [item for item in history if item['data'].get('torrentInfoHash', '').casefold() == torrentHash.casefold() or cleanFileName(item['sourceTitle'].casefold()) == torrent.file.fileInfo.filenameWithoutExt.casefold()]
    
    if not items:
        message = "No history items found to mark as failed. Arr will not attempt to grab an alternative."
        print(message)
        discordError(message, torrent.file.fileInfo.filenameWithoutExt)
    for item in items:
        arr.failHistoryItem(item['id'])
    print(f"Failed")

    timestamp = datetime.utcnow().isoformat() + "Z"
    discordUpdate(
        content=discord_user_tag if tag_on_failure else None,
        title=f"Failed To Process: {parsed_title}",
        message=f"**Debrid Provider:** {debrid_provider}\n{file_info}\n**STATUS:**\n⛔ Failed",
        color=16711680,  # Red for failure
        message_id=message_id,
        timestamp=timestamp
    )

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

        discordError(f"Error processing", f"Error:\n```{e}```")
    print("Exit 'on_created'")

if __name__ == "__main__":
    asyncio.run(on_created(isRadarr=sys.argv[1] == 'radarr'))
