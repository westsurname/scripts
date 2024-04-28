import os
import argparse
from shared.arr import Sonarr, Radarr
from shared.discord import discordUpdate
from shared.shared import intersperse

# Parse arguments for dry run and no confirm options
parser = argparse.ArgumentParser(description='Repair broken symlinks and manage media files.')
parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making any changes.')
parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation prompts.')
args = parser.parse_args()

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
            if args.dry_run or args.no_confirm or input("Do you want to delete and re-grab? (y/n): ").lower() == 'y':
                discordUpdate(f"Repairing... {media.title} - {childId}")
                print("Deleting files:")
                [print(childFile.path) for childFile in childFiles]
                if not args.dry_run:
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

