import os
import argparse
import time
import traceback
from shared.debrid import validateRealdebridMountTorrentsPath, validateTorboxMountTorrentsPath
from shared.arr import Sonarr, Radarr
from shared.discord import discordUpdate, discordError
from shared.shared import repair, realdebrid, torbox, intersperse, ensureTuple
from datetime import datetime

def parseInterval(intervalStr):
    """Parse a smart interval string (e.g., '1w2d3h4m5s') into seconds."""
    if not intervalStr:
        return 0
    totalSeconds = 0
    timeDict = {'w': 604800, 'd': 86400, 'h': 3600, 'm': 60, 's': 1}
    currentNumber = ''
    for char in intervalStr:
        if char.isdigit():
            currentNumber += char
        elif char in timeDict and currentNumber:
            totalSeconds += int(currentNumber) * timeDict[char]
            currentNumber = ''
    return totalSeconds
# Parse arguments for dry run, no confirm options, and optional intervals
parser = argparse.ArgumentParser(description='Repair broken symlinks or missing files.')
parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making any changes.')
parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation prompts.')
parser.add_argument('--repair-interval', type=str, default=repair['repairInterval'], help='Optional interval in smart format (e.g. 1h2m3s) to wait between repairing each media file.')
parser.add_argument('--run-interval', type=str, default=repair['runInterval'], help='Optional interval in smart format (e.g. 1w2d3h4m5s) to run the repair process.')
parser.add_argument('--mode', type=str, choices=['symlink', 'file'], default='symlink', help='Choose repair mode: `symlink` or `file`. `symlink` to repair broken symlinks and `file` to repair missing files.')
parser.add_argument('--include-unmonitored', action='store_true', help='Include unmonitored media in the repair process')
args = parser.parse_args()

_print = print

def print(*values: object):
    _print(f"[{datetime.now()}] [{args.mode}]", *values)

if not args.repair_interval and not args.run_interval:
    print("Running repair once")
else:
    print(f"Running repair{' once every ' + args.run_interval if args.run_interval else ''}{', and waiting ' + args.repair_interval + ' between each repair.' if args.repair_interval else '.'}")

try:
    repairIntervalSeconds = parseInterval(args.repair_interval)
except Exception as e:
    print(f"Invalid interval format for repair interval: {args.repair_interval}")
    exit(1)

try:
    runIntervalSeconds = parseInterval(args.run_interval)
except Exception as e:
    print(f"Invalid interval format for run interval: {args.run_interval}")
    exit(1)

def main():
    if unsafe():
        print("One or both debrid services are not working properly. Skipping repair.")
        discordError(f"[{args.mode}] One or both debrid services are not working properly. Skipping repair.")
        return
    
    print("Collecting media...")
    sonarr = Sonarr()
    radarr = Radarr()
    sonarrMedia = [(sonarr, media) for media in sonarr.getAll() if args.include_unmonitored or media.anyMonitoredChildren]
    radarrMedia = [(radarr, media) for media in radarr.getAll() if args.include_unmonitored or media.anyMonitoredChildren]
    print("Finished collecting media.")
    
    for arr, media in intersperse(sonarrMedia, radarrMedia):
        try:
            if unsafe():
                print("One or both debrid services are not working properly. Skipping repair.")
                discordError(f"[{args.mode}] One or both debrid services are not working properly. Skipping repair.")
                return 

            getItems = lambda media, childId: arr.getFiles(media=media, childId=childId) if args.mode == 'symlink' else arr.getHistory(media=media, childId=childId, includeGrandchildDetails=True)
            childrenIds = media.childrenIds if args.include_unmonitored else media.monitoredChildrenIds

            for childId in childrenIds:
                brokenItems = []
                childItems = list(getItems(media=media, childId=childId))

                for item in childItems:
                    if args.mode == 'symlink':
                        fullPath = item.path
                        if os.path.islink(fullPath):
                            destinationPath = os.readlink(fullPath)
                            if ((realdebrid['enabled'] and destinationPath.startswith(realdebrid['mountTorrentsPath']) and not os.path.exists(destinationPath)) or 
                               (torbox['enabled'] and destinationPath.startswith(torbox['mountTorrentsPath']) and not os.path.exists(os.path.realpath(fullPath)))):
                                brokenItems.append(os.path.realpath(fullPath))
                    else:  # file mode
                        if item.reason == 'MissingFromDisk' and item.parentId not in media.fullyAvailableChildrenIds:
                            brokenItems.append(item.sourceTitle)

                if brokenItems:
                    print("Title:", media.title)
                    print("Movie ID/Season Number:", childId)
                    print("Broken items:")
                    [print(item) for item in brokenItems]
                    print()
                    if args.dry_run or args.no_confirm or input("Do you want to delete and re-grab? (y/n): ").lower() == 'y':
                        if not args.dry_run:
                            discordUpdate(f"[{args.mode}] Repairing {media.title}: {childId}")
                            if args.mode == 'symlink':
                                print("Deleting files:")
                                [print(item.path) for item in childItems]
                                results = arr.deleteFiles(childItems)
                            print("Re-monitoring")
                            media = arr.get(media.id)
                            media.setChildMonitored(childId, False)
                            arr.put(media)
                            media.setChildMonitored(childId, True)
                            arr.put(media)
                            print("Searching for new files")
                            results = arr.automaticSearch(media, childId)
                            print(results)
                            
                            if repairIntervalSeconds > 0:
                                time.sleep(repairIntervalSeconds)
                    else:
                        print("Skipping")
                    print()
                elif args.mode == 'symlink':
                    realPaths = [os.path.realpath(item.path) for item in childItems]
                    parentFolders = set(os.path.dirname(path) for path in realPaths)
                    if childId in media.fullyAvailableChildrenIds and len(parentFolders) > 1:
                        print("Title:", media.title)
                        print("Movie ID/Season Number:", childId)
                        print("Inconsistent folders:")
                        [print(parentFolder) for parentFolder in parentFolders]
                        print()
        except Exception:
            e = traceback.format_exc()

            print(f"An error occurred while processing {media.title}: {e}")
            discordError(f"[{args.mode}] An error occurred while processing {media.title}", e)

    print("Repair complete")
    discordUpdate(f"[{args.mode}] Repair complete")

def unsafe():
    return (args.mode == 'symlink' and 
        ((realdebrid['enabled'] and not ensureTuple(validateRealdebridMountTorrentsPath())[0]) or 
        (torbox['enabled'] and not ensureTuple(validateTorboxMountTorrentsPath())[0])))

if runIntervalSeconds > 0:
    while True:
        try:
            main()
            time.sleep(runIntervalSeconds)
        except Exception:
            e = traceback.format_exc()

            print(f"An error occurred in the main loop: {e}")
            discordError(f"[{args.mode}] An error occurred in the main loop", e)
            time.sleep(runIntervalSeconds)  # Still wait before retrying
else:
    main()
