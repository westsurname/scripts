import os
from shared.arr import Sonarr, Radarr
from shared.discord import discordUpdate
from shared.shared import intersperse

sonarr = Sonarr()
radarr = Radarr()
sonarrMedia = [(sonarr, media) for media in sonarr.getAll() if media.anyMonitoredChildren]
radarrMedia = [(radarr, media) for media in radarr.getAll() if media.anyMonitoredChildren]

for arr, media in intersperse(sonarrMedia, radarrMedia):  
    files = {}
    for file in arr.getFiles(media):
        if file.parentId in files:
            files[file.parentId].append(file)
        else:
            files[file.parentId] = [file]
    for childId in media.monitoredChildrenIds:
        realPaths = []
        brokenSymlinks = []

        childFiles = files.get(childId, [])
        for childFile in childFiles:

            fullPath = childFile.path
            realPath = os.path.realpath(fullPath)
            realPaths.append(realPath)
            

            if os.path.islink(fullPath) and not os.path.exists(realPath):
                brokenSymlinks.append(realPath)
        
        # If not full season just repair individual episodes?
        if brokenSymlinks:
            print("Title:", media.title)
            print("Movie ID/Season Number:", childId)
            print("Broken symlinks:")
            [print(brokenSymlink) for brokenSymlink in brokenSymlinks]
            print()
            if input("Do you want to perform an automatic search? (y/n): ").lower() == 'y':
                discordUpdate(f"Repairing... {media.title} - {childId}")
                print("Deleting files:")
                [print(childFile.path) for childFile in childFiles]
                results = arr.deleteFiles(childFiles)
                print("Remonitoring")
                media = arr.get(media.id)
                media.setChildMonitored(childId, False)
                arr.put(media)
                media.setChildMonitored(childId, True)
                arr.put(media)
                print("Searching for new files")
                results = arr.automaticSearch(media, childId)
                print(results)
            else:
                print("Skipping")
            print()
        else:
            parentFolders = set(os.path.dirname(path) for path in realPaths)
            if childId in media.fullyAvailableChildrenIds and len(parentFolders) > 1:
                print("Title:", media.title)
                print("Movie ID/Season Number:", childId)
                print("Inconsistent folders:")
                [print(parentFolder) for parentFolder in parentFolders]
                print()

