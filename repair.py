import os
import argparse
import time
from datetime import timedelta
from shared.arr import Sonarr, Radarr
from shared.discord import discordUpdate
from shared.shared import intersperse

def parse_interval(interval_str):
    """Parse a smart interval string formatted like a YouTube timestamp (e.g., '1h2m3s') into seconds."""
    if not interval_str:
        return 0
    total_seconds = 0
    time_dict = {'h': 3600, 'm': 60, 's': 1}
    current_number = ''
    for char in interval_str:
        if char.isdigit():
            current_number += char
        elif char in time_dict and current_number:
            total_seconds += int(current_number) * time_dict[char]
            current_number = ''
    return total_seconds

# Parse arguments for dry run, no confirm options, and optional interval
parser = argparse.ArgumentParser(description='Repair broken symlinks and manage media files.')
parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making any changes.')
parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation prompts.')
parser.add_argument('--interval', type=str, default='', help='Optional interval in smart format (e.g. 1h2m3s) to wait between processing each media file.')
args = parser.parse_args()

# Convert interval from smart format to seconds
try:
    interval_seconds = parse_interval(args.interval)
except Exception as e:
    print(f"Invalid interval format: {args.interval}")
    exit(1)

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

        if interval_seconds > 0:
            time.sleep(interval_seconds)

