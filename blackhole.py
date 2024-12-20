from mimetypes import add_type
from dis import code_info
import shutil
import time
import traceback
import os
import sys
import re
import asyncio
from datetime import datetime
from typing import Optional, List
from shared.discord import discordError, discordUpdate
from shared.shared import realdebrid, torbox, blackhole, plex, checkRequiredEnvs
from shared.arr import Arr, Radarr, Sonarr
from shared.debrid import TorrentBase, RealDebridTorrent, RealDebridMagnet, TorboxTorrent, TorboxMagnet
from shared.websocket import WebSocketManager
from dotenv import load_dotenv

load_dotenv()

# Add helper functions here, before any other code
def extract_year(filename: str) -> Optional[int]:
    """Extract year from filename."""
    match = re.search(r'(?:19|20)\d{2}', filename)
    return int(match.group(0)) if match else None

def extract_season(filename: str) -> Optional[List[int]]:
    """Extract season numbers from filename."""
    matches = re.findall(r'S(\d{1,2})(?:E\d{1,2})?', filename, re.IGNORECASE)
    return [int(m) for m in matches] if matches else None

def extract_episode(filename: str) -> Optional[List[int]]:
    """Extract episode numbers from filename."""
    matches = re.findall(r'E(\d{1,2})', filename, re.IGNORECASE)
    return [int(m) for m in matches] if matches else None

def extractResolution(filename: str) -> list[str]:
    """Extract resolution from filename."""
    resolutions = ['2160p', '1080p', '720p', '480p']
    return [res for res in resolutions if res.lower() in filename.lower()]

def extractCodec(filename: str) -> list[str]:
    """Extract codec from filename."""
    codecs = ['x265', 'x264', 'HEVC', 'AVC', 'H264', 'H.264']
    return [codec for codec in codecs if codec.lower() in filename.lower()]

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
    def __init__(self, filename, isRadarr) -> None:
        print('filename:', filename)
        self.id = filename  # Use filename as consistent ID
        self.fileInfo = self.FileInfo(filename, os.path.splitext(filename)[0], 
                                    os.path.join(getPath(isRadarr), filename),
                                    os.path.join(getPath(isRadarr), 'processing', filename),
                                    os.path.join(getPath(isRadarr), 'completed', os.path.splitext(filename)[0]))
        self.torrentInfo = self.TorrentInfo(
            filename.casefold().endswith('.torrent') or filename.casefold().endswith('.magnet'),
            filename.casefold().endswith('.torrent')
        )

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
        for i in range(count):
            arr.refreshMonitoredDownloads()
            ws_manager = WebSocketManager.get_instance()
            current_items = ws_manager.get_active_items()
            for item_id, item in current_items.items():
                if item['status'].get('imported'):
                    item['status'].update({
                        'status': f'Refreshing ({i+1}/{count})',
                        'progress': 100,
                        'cached': True,
                        'added': True,
                        'mounted': True,
                        'symlinked': True,
                        'imported': True
                    })
            
            if i % 10 == 0:  # Only log every 10th refresh
                print(f"[REFRESH] Progress: {i+1}/{count}")
            
            await ws_manager.broadcast_status({
                'type': 'processing_status',
                'items': list(current_items.values())
            })
            await asyncio.sleep(1)

    global refreshingTask
    if refreshingTask and not refreshingTask.done():
        print("[REFRESH] Restarting existing refresh task")
        refreshingTask.cancel()

    refreshingTask = asyncio.create_task(refresh())
    try:
        await refreshingTask
        print("[REFRESH] Complete")
        return True
    except asyncio.CancelledError:
        print("[REFRESH] Cancelled")
        return False

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
    info = None

    def print(*values: object):
        _print(f"[{torrent.__class__.__name__}] [{file.fileInfo.filenameWithoutExt}]", *values)
        
    async def send_status_update(status_dict):
        nonlocal info
        if 'status' not in status_dict:
            status_dict['status'] = 'Unknown'
        
        parsed_info = await asyncio.to_thread(arr.parse, file.fileInfo.filenameWithoutExt)
        if parsed_info:
            status_dict['parsedInfo'] = parsed_info
        
        ws_manager = WebSocketManager.get_instance()
        current_items = ws_manager.get_active_items()
        
        current_item = {
            'id': file.fileInfo.filename,
            'title': file.fileInfo.filenameWithoutExt,
            'type': 'movie' if isinstance(arr, Radarr) else 'series',
            'status': status_dict,
            'progress': status_dict.get('progress', 0),
            'debridProvider': torrent.__class__.__name__,
            'fileInfo': {
                'name': file.fileInfo.filename,
                'resolution': extractResolution(file.fileInfo.filename),
                'codec': extractCodec(file.fileInfo.filename),
                'year': extract_year(file.fileInfo.filename),
                'season': extract_season(file.fileInfo.filename),
                'episode': extract_episode(file.fileInfo.filename)
            }
        }
        
        current_items[file.fileInfo.filename] = current_item
        
        # Only log status changes
        print(f"[STATUS] {file.fileInfo.filenameWithoutExt}: {status_dict['status']} (imported={status_dict.get('imported', False)})")
        
        await ws_manager.broadcast_status({
            'type': 'processing_status',
            'items': list(current_items.values())
        })
        
        # Add a small delay after each status update to ensure it's visible
        await asyncio.sleep(0.1)

    async def handle_error(error_status, error_message):
        current_status.update({
            'status': error_status,
            'error': True,
            'progress': 0,
            'errorTime': int(time.time())
        })
        await send_status_update(current_status)
        print(f"Error: {error_message}")
        discordError(error_status, error_message)
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_status({
            'type': 'notification',
            'notification': {
                'type': 'error',
                'title': error_status,
                'message': f"{file.fileInfo.filenameWithoutExt}: {error_message}",
                'timestamp': int(time.time())
            }
        })
        ws_manager.remove_active_item(file.fileInfo.filename)
        return False

    current_status = {
        'cached': False,
        'added': False,
        'mounted': False,
        'symlinked': False,
        'status': 'Initializing',
        'progress': 0
    }
    await send_status_update(current_status)
    
    if not torrent.submitTorrent():
        current_status.update({
            'status': 'Failed to submit torrent',
            'error': True,
            'progress': 0,
            'errorTime': int(time.time())
        })
        await send_status_update(current_status)
        print(f"Failed to submit torrent: {file.fileInfo.filenameWithoutExt}")
        discordError("Failed to submit torrent", file.fileInfo.filenameWithoutExt)
        
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_status({
            'type': 'notification',
            'notification': {
                'type': 'error',
                'title': 'Failed to submit torrent',
                'message': f"{file.fileInfo.filenameWithoutExt}",
                'timestamp': int(time.time())
            }
        })
        ws_manager.remove_active_item(file.fileInfo.filename)
        return False

    count = 0
    while True:
        count += 1
        info = await torrent.getInfo(refresh=True)
        if not info:
            current_status.update({
                'status': 'Waiting for torrent info',
                'cached': False,
                'progress': 5
            })
            await send_status_update(current_status)
            await asyncio.sleep(1)
            continue
            
        status = info.get('status')
        progress = info.get('progress', 0)
        cached = info.get('cached', False)
        
        print('status:', status)

        current_status.update({
            'cached': cached,
            'progress': progress
        })

        if cached:
            current_status.update({
                'status': 'Cached',
                'added': True,
                'cached': True
            })
        elif status == torrent.STATUS_WAITING_FILES_SELECTION:
            current_status.update({
                'status': 'Selecting files',
                'added': True,
                'progress': 25
            })
            await send_status_update(current_status)
            
            if not await torrent.selectFiles():
                current_status.update({
                    'status': 'File selection failed',
                    'error': True,
                    'progress': 0
                })
                await send_status_update(current_status)
                torrent.delete()
                return False

        elif status == torrent.STATUS_DOWNLOADING:
            current_status.update({
                'status': 'Downloading',
                'added': True
            })
            print(f"Progress: {progress:.2f}%")
            
            if torrent.incompatibleHashSize and torrent.failIfNotCached:
                current_status.update({
                    'status': 'Non-cached incompatible hash',
                    'error': True,
                    'progress': 0,
                    'errorTime': int(time.time())
                })
                await send_status_update(current_status)
                print(f"Non-cached incompatible hash detected for {file.fileInfo.filenameWithoutExt}")
                discordError("Non-cached incompatible hash", f"{file.fileInfo.filenameWithoutExt}")
                ws_manager = WebSocketManager.get_instance()
                await ws_manager.broadcast_status({
                    'type': 'notification',
                    'notification': {
                        'type': 'error',
                        'title': 'Non-cached incompatible hash',
                        'message': f"{file.fileInfo.filenameWithoutExt}",
                        'timestamp': int(time.time())
                    }
                })
                ws_manager.remove_active_item(file.fileInfo.filename)
                return False

        elif status == torrent.STATUS_ERROR:
            current_status.update({
                'status': 'Error occurred',
                'error': True,
                'progress': 0
            })
            await send_status_update(current_status)
            return False

        elif status == torrent.STATUS_COMPLETED:
            current_status.update({
                'status': 'Waiting for folders',
                'added': True,
                'cached': True,
                'progress': 50
            })
            await send_status_update(current_status)
            
            existsCount = 0
            print('Waiting for folders to refresh...')

            while True:
                existsCount += 1
                folderPathMountTorrent = await torrent.getTorrentPath()
                
                if folderPathMountTorrent:
                    current_status.update({
                        'status': 'Creating symlinks',
                        'cached': True,
                        'mounted': True,
                        'progress': 75
                    })
                    await send_status_update(current_status)
                    
                    multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
                    multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
                    multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'
                    multiSeasonMatch = re.search(multiSeasonRegexCombined, file.fileInfo.filenameWithoutExt)
                    
                    symlinks_created = False
                    try:
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
                                        symlinks_created = True
                                        continue

                                os.makedirs(os.path.join(file.fileInfo.folderPathCompleted, relRoot), exist_ok=True)
                                os.symlink(os.path.join(root, filename), os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename))
                                print('Recursive:', f"{os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)} -> {os.path.join(root, filename)}")
                                symlinks_created = True
                        
                        if symlinks_created:
                            current_status.update({
                                'symlinked': True,
                                'status': 'Symlinks created',
                                'progress': 85
                            })
                            await send_status_update(current_status)
                    except Exception as e:
                        print(f"Error creating symlinks: {e}")
                        return await handle_error('Symlink creation failed', str(e))
                    
                    # Give UI time to show symlink status
                    await asyncio.sleep(2)
                    
                    # First mark as importing
                    current_status.update({
                        'status': f'Importing to {"Radarr" if isinstance(arr, Radarr) else "Sonarr"}',
                        'cached': True,
                        'added': True,
                        'mounted': True,
                        'symlinked': True,
                        'imported': False,
                        'progress': 95
                    })
                    await send_status_update(current_status)

                    # Start refresh process before marking as complete
                    print(f"[PROCESS] Starting refresh for {file.fileInfo.filenameWithoutExt}")
                    refresh_complete = await refreshArr(arr)
                    print(f"[PROCESS] Refresh completed: {refresh_complete}")

                    if refresh_complete:
                        # Now mark as complete after refresh
                        current_status.update({
                            'status': 'Complete',
                            'cached': True,
                            'added': True,
                            'mounted': True,
                            'symlinked': True,
                            'imported': True,
                            'progress': 100,
                            'completedTime': int(time.time())
                        })
                        await send_status_update(current_status)
                        
                        # Send notification
                        print(f"[PROCESS] Sending completion notification for {file.fileInfo.filenameWithoutExt}")
                        ws_manager = WebSocketManager.get_instance()
                        await ws_manager.broadcast_status({
                            'type': 'notification',
                            'notification': {
                                'type': 'success',
                                'title': 'Processing Complete',
                                'message': f"Successfully processed {file.fileInfo.filenameWithoutExt}",
                                'timestamp': int(time.time())
                            }
                        })
                        
                        print(f"[PROCESS] Waiting before removal of {file.fileInfo.filenameWithoutExt}")
                        await asyncio.sleep(5)
                        
                        print(f"[PROCESS] Removing {file.fileInfo.filenameWithoutExt}")
                        ws_manager.remove_active_item(file.fileInfo.filename)
                        print(f"[PROCESS] Removed {file.fileInfo.filenameWithoutExt}")
                        
                        return True
                    
                    print(f"[PROCESS] Refresh failed for {file.fileInfo.filenameWithoutExt}")
                    return False

                if existsCount >= blackhole['rdMountRefreshSeconds'] + 1:
                    current_status.update({
                        'status': 'Folder not found in filesystem',
                        'error': True,
                        'progress': 0
                    })
                    await send_status_update(current_status)
                    print(f"Torrent folder not found in filesystem: {file.fileInfo.filenameWithoutExt}")
                    discordError("Torrent folder not found in filesystem", file.fileInfo.filenameWithoutExt)
                    return False

                await asyncio.sleep(1)
        
        await send_status_update(current_status)
        
        if status == torrent.STATUS_ERROR:
            return await handle_error('Error occurred', f"Debrid provider error for {file.fileInfo.filenameWithoutExt}")

        if torrent.failIfNotCached and count >= blackhole['waitForTorrentTimeout']:
            current_status.update({
                'status': 'Timeout reached',
                'error': True,
                'progress': 0
            })
            await send_status_update(current_status)
            print(f"Torrent timeout: {file.fileInfo.filenameWithoutExt} - {status}")
            discordError("Torrent timeout", f"{file.fileInfo.filenameWithoutExt} - {status}")
            return False

        await asyncio.sleep(1)

    # When reaching completion point:
    print(f"[PROCESS] Starting completion for {file.fileInfo.filenameWithoutExt}")
    
    # First mark as importing
    current_status.update({
        'status': f'Importing to {"Radarr" if isinstance(arr, Radarr) else "Sonarr"}',
        'cached': True,
        'added': True,
        'mounted': True,
        'symlinked': True,
        'imported': False,
        'progress': 95
    })
    await send_status_update(current_status)

    # Start refresh process before marking as complete
    print(f"[PROCESS] Starting refresh for {file.fileInfo.filenameWithoutExt}")
    refresh_complete = await refreshArr(arr)
    print(f"[PROCESS] Refresh completed: {refresh_complete}")

    if refresh_complete:
        # Now mark as complete after refresh
        current_status.update({
            'status': 'Complete',
            'cached': True,
            'added': True,
            'mounted': True,
            'symlinked': True,
            'imported': True,
            'progress': 100,
            'completedTime': int(time.time())  # Add completion timestamp
        })
        await send_status_update(current_status)
        
        # Send notification
        print(f"[PROCESS] Sending completion notification for {file.fileInfo.filenameWithoutExt}")
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_status({
            'type': 'notification',
            'notification': {
                'type': 'success',
                'title': 'Processing Complete',
                'message': f"Successfully processed {file.fileInfo.filenameWithoutExt}",
                'timestamp': int(time.time())
            }
        })
        
        print(f"[PROCESS] Waiting before removal of {file.fileInfo.filenameWithoutExt}")
        await asyncio.sleep(5)
        
        print(f"[PROCESS] Removing {file.fileInfo.filenameWithoutExt}")
        ws_manager.remove_active_item(file.fileInfo.filename)
        print(f"[PROCESS] Removed {file.fileInfo.filenameWithoutExt}")
        
        return True
    
    print(f"[PROCESS] Refresh failed for {file.fileInfo.filenameWithoutExt}")
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
                    return True
                except Exception as e:
                    print(f"Error accessing file: {e}")
                    return False
                finally:
                    executor.shutdown(wait=False)

        time.sleep(.1)
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
            
            # Send initial status with consistent ID
            ws_manager = WebSocketManager.get_instance()
            await ws_manager.broadcast_status({
                'type': 'processing_status',
                'items': [{
                    'id': file.id,
                    'title': file.fileInfo.filenameWithoutExt,
                    'type': 'movie' if isRadarr else 'series',
                    'status': {
                        'cached': False,
                        'added': False,
                        'mounted': False,
                        'symlinked': False,
                        'imported': False,  # Added imported status
                        'status': 'Starting',
                        'progress': 0
                    },
                    'progress': 0,
                    'debridProvider': '',
                    'fileInfo': {
                        'name': file.fileInfo.filename,
                        'resolution': extractResolution(file.fileInfo.filename),
                        'codec': extractCodec(file.fileInfo.filename),
                        'year': extract_year(file.fileInfo.filename),
                        'season': extract_season(file.fileInfo.filename),
                        'episode': extract_episode(file.fileInfo.filename)
                    }
                }]
            })

            if not blackhole['failIfNotCached']:
                torrents = [constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile) for constructor in torrentConstructors]
                results = await asyncio.gather(*(processTorrent(torrent, file, arr) for torrent in torrents))
                
                if not any(results):
                    await asyncio.gather(*(fail(torrent, arr) for torrent in torrents))
                    # Ensure item is removed after failure
                    ws_manager = WebSocketManager.get_instance()
                    ws_manager.remove_active_item(file.id)
            else:
                success = False
                for i, constructor in enumerate(torrentConstructors):
                    isLast = (i == len(torrentConstructors) - 1)
                    torrent = constructor(f, fileData, file, blackhole['failIfNotCached'], onlyLargestFile)

                    if await processTorrent(torrent, file, arr):
                        success = True
                        break
                    elif isLast:
                        await fail(torrent, arr)
                        # Ensure item is removed after failure
                        ws_manager = WebSocketManager.get_instance()
                        ws_manager.remove_active_item(file.id)

            os.remove(file.fileInfo.filePathProcessing)
    except:
        e = traceback.format_exc()
        print(f"Error processing {file.fileInfo.filenameWithoutExt}")
        print(e)
        discordError(f"Error processing {file.fileInfo.filenameWithoutExt}", e)
        
        # Clean up WebSocket status and ensure item is removed
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_status({
            'type': 'notification',
            'notification': {
                'type': 'error',
                'title': 'Processing Error',
                'message': f"Error processing {file.fileInfo.filenameWithoutExt}",
                'timestamp': int(time.time())
            }
        })
        ws_manager.remove_active_item(file.id)

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

def main():
    print("Starting blackhole watcher")

async def handle_delete_request(item_id: str):
    ws_manager = WebSocketManager.get_instance()
    if item_id in ws_manager.get_active_items():
        # Remove from active items
        ws_manager.remove_active_item(item_id)
        
        # Find and remove the processing file if it exists
        for isRadarr in [True, False]:
            processing_path = os.path.join(getPath(isRadarr), 'processing', item_id)
            if os.path.exists(processing_path):
                try:
                    os.remove(processing_path)
                    print(f"Removed processing file: {item_id}")
                    return True
                except Exception as e:
                    print(f"Error removing processing file {item_id}: {e}")
                    return False
    return False

if __name__ == "__main__":
    asyncio.run(on_created(isRadarr=sys.argv[1] == 'radarr'))
