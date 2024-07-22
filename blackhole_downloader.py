import asyncio
import os
import glob
from shared.discord import discordError, discordUpdate, discordStatusUpdate
from shared.shared import blackhole
import re

async def downloader(torrent, file, arr, torrentFile, shared_dict, lock, webhook):
    from blackhole import refreshArr
    availableHost = torrent.getAvailableHost()
    activeTorrents = torrent.getActiveTorrents()

    while True:
        if activeTorrents['limit'] - activeTorrents['nb'] > 0:
            allTorrents = torrent.getAllTorrents()
            torrentExists = False
            for at in allTorrents:
                if at["hash"] == torrent.getHash().lower():
                    torrent.id = at["id"]
                    torrentName = at["filename"]
                    if at["status"] == "downloaded":
                        print("File already exists")
                    elif at["status"] == "downloading":
                        print("File downloading")
                    torrentExists = True
                    lock.acquire()
                    if torrentName in shared_dict:
                        lock.release()
                        remove_file(torrentFile, lock, shared_dict, torrentName, webhook)
                        return
                    lock.release()
                    break
            if not torrentExists:
                while True:
                    folder_path = os.path.dirname(torrentFile)
                    all_files = glob.glob(os.path.join(folder_path, '*'))
                    all_files.sort(key=os.path.getctime)
                    top_4_files = all_files[:4]
                    if torrentFile in top_4_files:
                        torrent.getInstantAvailability()
                        torrent.addTorrent(availableHost)
                        info = torrent.getInfo(refresh=True)
                        torrentName = info['filename']
                        lock.acquire()
                        try:
                            if shared_dict:
                                shared_dict.update({torrentName : "added"})
                                discordStatusUpdate(shared_dict, webhook, edit=True)
                            else:
                                shared_dict.update({torrentName : "added"})
                                discordStatusUpdate(shared_dict, webhook)
                        finally:
                            lock.release()
                        break
                    if not os.path.exists(torrentFile):
                        break
                    await asyncio.sleep(60)
            break
        await asyncio.sleep(60)
    
    count = 0
    while True:
        count += 1
        info = torrent.getInfo(refresh=True)
        status = info['status']
        torrentName = info['filename']
        
        print('status:', status)
        if not os.path.exists(torrentFile):
            torrent.delete()
            break
        if status == 'waiting_files_selection':
            if not torrent.selectFiles():
                torrent.delete()
                break
        elif status == 'magnet_conversion' or status == 'queued' or status == 'downloading' or status == 'compressing' or status == 'uploading':
            progress = info['progress']
            print(progress)
            lock.acquire()
            try:
                if shared_dict:
                    shared_dict.update({torrentName : f"Downloading {progress}%"})
                    discordStatusUpdate(shared_dict, webhook, edit=True)
                else:
                    shared_dict.update({torrentName : f"Downloading {progress}%"})
                    discordStatusUpdate(shared_dict, webhook)
            finally:
                lock.release()
            if torrent.incompatibleHashSize and torrent.failIfNotCached:
                print("Non-cached incompatible hash sized torrent")
                torrent.delete()
                break
            await asyncio.sleep(5)
        elif status == 'magnet_error' or status == 'error' or status == 'dead' or status == 'virus':
            torrent.delete()
            break
        elif status == 'downloaded':
            existsCount = 0
            print('Waiting for folders to refresh...')

            filename = info.get('filename')
            originalFilename = info.get('original_filename')

            folderPathMountFilenameTorrent = os.path.join(blackhole['rdMountTorrentsPath'], filename)
            folderPathMountOriginalFilenameTorrent = os.path.join(blackhole['rdMountTorrentsPath'], originalFilename)
            folderPathMountOriginalFilenameWithoutExtTorrent = os.path.join(blackhole['rdMountTorrentsPath'], os.path.splitext(originalFilename)[0])

            while existsCount <= blackhole['waitForTorrentTimeout']:
                existsCount += 1
                
                if os.path.exists(folderPathMountFilenameTorrent) and os.listdir(folderPathMountFilenameTorrent):
                    folderPathMountTorrent = folderPathMountFilenameTorrent
                elif os.path.exists(folderPathMountOriginalFilenameTorrent) and os.listdir(folderPathMountOriginalFilenameTorrent):
                    folderPathMountTorrent = folderPathMountOriginalFilenameTorrent
                elif (originalFilename.endswith(('.mkv', '.mp4')) and
                        os.path.exists(folderPathMountOriginalFilenameWithoutExtTorrent) and os.listdir(folderPathMountOriginalFilenameWithoutExtTorrent)):
                    folderPathMountTorrent = folderPathMountOriginalFilenameWithoutExtTorrent
                else:
                    folderPathMountTorrent = None

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
                                    continue


                            os.makedirs(os.path.join(file.fileInfo.folderPathCompleted, relRoot), exist_ok=True)
                            os.symlink(os.path.join(root, filename), os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename))
                            print('Recursive:', f"{os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)} -> {os.path.join(root, filename)}")
                    
                    print('Refreshed')
                    discordUpdate(f"Sucessfully processed {file.fileInfo.filenameWithoutExt}", f"Now available for immediate consumption! existsCount: {existsCount}")
                    
                    await refreshArr(arr)
                    break
                
                if existsCount == blackhole['rdMountRefreshSeconds'] + 1:
                    print(f"Torrent folder not found in filesystem: {file.fileInfo.filenameWithoutExt}")
                    discordError("Torrent folder not found in filesystem", file.fileInfo.filenameWithoutExt)

                await asyncio.sleep(1)
            break
    
        if torrent.failIfNotCached:
            if count == 21 and status != "downloading":
                print('infoCount > 20')
                discordError(f"{file.fileInfo.filenameWithoutExt} info attempt count > 20", status)
            elif count == blackhole['waitForTorrentTimeout']:
                print(f"infoCount == {blackhole['waitForTorrentTimeout']} - Failing")
                torrent.delete()
                break
    remove_file(torrentFile, lock, shared_dict, torrentName, webhook)
    
def remove_file(torrentFile, lock, shared_dict, torrentName, webhook):
    if os.path.exists(torrentFile):
        folder_path = os.path.dirname(torrentFile)
        all_files = glob.glob(os.path.join(folder_path, '*'))
        all_files.sort(key=os.path.getctime)
        try:
            file_index = all_files.index(torrentFile)
        except ValueError:
            print("The file does not exist in the folder.")
            file_index = -1

        if file_index != -1:
            files_to_remove = all_files[file_index:]
            for file in files_to_remove:
                try:
                    os.remove(file)
                    print(f"Removed: {file}")
                except Exception as e:
                    print(f"Error removing {file}: {e}")

            remaining_files = os.listdir(folder_path)
            if not remaining_files:
                try:
                    os.rmdir(folder_path)
                    print(f"Removed folder: {folder_path}")
                except Exception as e:
                    print(f"Error removing folder {folder_path}: {e}")
            else:
                print(f"Folder is not empty: {folder_path}")
        else:
            print("The specified file is not in the folder.")
    else:
        print("The file does not exist.")

    lock.acquire()
    try:
        if torrentName in shared_dict:
            del shared_dict[torrentName]
        if shared_dict:
            discordStatusUpdate(shared_dict, webhook, edit=True)
        else:
            discordStatusUpdate(shared_dict, webhook, delete=True)
    finally:
        lock.release()