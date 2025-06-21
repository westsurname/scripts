import os
import argparse
import asyncio
import time
import traceback
import threading
from collections import defaultdict
from shared.debrid import validateRealdebridMountTorrentsPath, validateTorboxMountTorrentsPath
from shared.arr import Sonarr, Radarr
from shared.discord import discordUpdate as _discordUpdate, discordError as _discordError
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

async def checkAutomaticSearchStatus(arr, commandId: int, mediaTitle: str, mediaDescriptor: str, waitSeconds: int = 30, maxAttempts: int = 3):
    """
    Check the automatic search status up to maxAttempts, waiting waitSeconds between each check.
    Stops early if searchSuccessful is no longer None.
    """
    for attempt in range(0, maxAttempts):
        await asyncio.sleep(waitSeconds)
        searchStatus = arr.getCommandResults(commandId)
        
        searchSuccessful = True if (status := searchStatus.get("status")) == "completed" else False if status == "failed" else None
        if searchSuccessful is None:
            continue
        message = searchStatus.get("message", "")

        if searchSuccessful and "0 reports downloaded." not in message:
            successMsg = f"Search for {mediaTitle} {mediaDescriptor} succeeded: {message}"
            print(successMsg, level="SUCCESS")
            return
        else:
            errorMsg = f"Search for {mediaTitle} {mediaDescriptor} failed: {message}"
            print(errorMsg, level="ERROR")
            discordError(errorMsg)
            return
    # If we exit the loop, the status was still None after maxAttempts
    print(f"Search status for {mediaTitle} {mediaDescriptor} still unknown after {maxAttempts*waitSeconds} seconds. Not checking anymore.", level="WARNING")
    
def runAsyncInThread(coro):
    """
    Run an async coroutine in a new thread with its own event loop.
    """
    def threadTarget():
        # Each thread needs its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
        loop.close()
    
    thread = threading.Thread(target=threadTarget)
    thread.daemon = True  # Optional: thread won’t block program exit
    thread.start()
    return thread

# Parse arguments for dry run, no confirm options, and optional intervals
parser = argparse.ArgumentParser(description='Repair broken symlinks or missing files.')
parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making any changes.')
parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation prompts.')
parser.add_argument('--repair-interval', type=str, default=repair['repairInterval'], help='Optional interval in smart format (e.g. 1h2m3s) to wait between repairing each media file.')
parser.add_argument('--run-interval', type=str, default=repair['runInterval'], help='Optional interval in smart format (e.g. 1w2d3h4m5s) to run the repair process.')
parser.add_argument('--mode', type=str, choices=['symlink', 'file'], default='symlink', help='Choose repair mode: `symlink` or `file`. `symlink` to repair broken symlinks and `file` to repair missing files.')
parser.add_argument('--season-packs', action='store_true', help='Upgrade to season-packs when a non-season-pack is found. Only applicable in symlink mode.')
parser.add_argument('--include-unmonitored', action='store_true', help='Include unmonitored media in the repair process')
args = parser.parse_args()

_print = print

def print(*values: object, level: str = "INFO"):
    prefix = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{args.mode}] [{level}] "
    _print(prefix, *values)
    
def printSection(title: str, char: str = "="):
    """Print a section header."""
    line = char * (len(title) + 4)
    print(line)
    print(f"  {title.upper()}")
    print(line)
    print()
        
def discordUpdate(title: str, message: str = None):
    return _discordUpdate(f"[{args.mode}] {title}", message)

def discordError(title: str, message: str = None):
    return _discordError(f"[{args.mode}] {title}", message)

if not args.repair_interval and not args.run_interval:
    print("Running repair once")
else:
    print(f"Running repair{' once every ' + args.run_interval if args.run_interval else ''}{', and waiting ' + args.repair_interval + ' between each repair.' if args.repair_interval else '.'}")
print()

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
    printSection("Starting Repair Process")
    if args.dry_run:
        print("DRY RUN: No changes will be made", level="WARNING")
    if unsafe():
        error_msg = "One or both debrid services are not working properly. Skipping repair."
        print(error_msg, level="ERROR")
        discordError(error_msg)
        return
    
    print("Collecting media from Sonarr and Radarr...")
    sonarr = Sonarr()
    radarr = Radarr()
    sonarrMedia = [(sonarr, media) for media in sonarr.getAll() if args.include_unmonitored or media.anyMonitoredChildren]
    radarrMedia = [(radarr, media) for media in radarr.getAll() if args.include_unmonitored or media.anyMonitoredChildren]
    print(f"✓ Collected {len(sonarrMedia)} Sonarr items and {len(radarrMedia)} Radarr items", level="SUCCESS")
    print()

    fixedBrokenItems = False
    seasonPackPendingMessages = defaultdict(lambda: defaultdict(list))
    
    for arr, media in intersperse(sonarrMedia, radarrMedia):
        try:
            if unsafe():
                error_msg = "One or more debrid services are not working properly. Aborting repair."
                print(error_msg, level="ERROR")
                discordError(error_msg)
                return

            getItems = lambda media, childId: arr.getFiles(media=media, childId=childId) if args.mode == 'symlink' else arr.getHistory(media=media, childId=childId, includeGrandchildDetails=True)
            childrenIds = media.childrenIds if args.include_unmonitored else media.monitoredChildrenIds

            for childId in childrenIds:
                brokenItems = []
                childItems = list(getItems(media=media, childId=childId))
                parentFolders = set()
                mediaDescriptor = f"(Season {childId})" if isinstance(arr, Sonarr) else f"(Movie ID: {childId})"

                for item in childItems:
                    if args.mode == 'symlink':
                        fullPath = item.path
                        if os.path.islink(fullPath):
                            destinationPath = os.readlink(fullPath)
                            parentFolders.add(os.path.dirname(os.path.realpath(fullPath)))
                            if ((realdebrid['enabled'] and destinationPath.startswith(realdebrid['mountTorrentsPath']) and not os.path.exists(destinationPath)) or 
                               (torbox['enabled'] and destinationPath.startswith(torbox['mountTorrentsPath']) and not os.path.exists(os.path.realpath(fullPath)))):
                                brokenItems.append(os.path.realpath(fullPath))
                    else:  # file mode
                        if item.reason == 'MissingFromDisk' and item.parentId not in media.fullyAvailableChildrenIds:
                            brokenItems.append(item.sourceTitle)

                if brokenItems:
                    fixedBrokenItems = True
                    msg = f"Repairing {media.title} {mediaDescriptor}"
                    msg2 = f"Found {len(brokenItems)} broken items:"
                    printSection(msg, "-")
                    print(msg2)
                    [print(item) for item in brokenItems]
                    if not args.dry_run and (args.no_confirm or input("Do you want to delete and re-grab? (y/n): ").lower() == 'y'):
                        discordUpdate(msg, msg2)
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
                        print(f"Searching for replacement files for {media.title}")
                        results = arr.automaticSearch(media, childId)
                        runAsyncInThread(checkAutomaticSearchStatus(arr, results['id'], media.title, mediaDescriptor))
                        
                        if repairIntervalSeconds > 0:
                            print(f"Waiting {args.repair_interval} before next repair...")
                            time.sleep(repairIntervalSeconds)
                    else:
                        print("Skipping")
                    print()
                elif args.mode == 'symlink':
                    if childId in media.fullyAvailableChildrenIds and len(parentFolders) > 1:
                        if not args.season_packs:
                            seasonPackPendingMessages[media.title][childId].extend(parentFolders)
                        else:
                            printSection(f"Searching for season-pack for {media.title} (Season {childId})", "-")
                            print("Non-season-pack folders:")
                            [print(path) for path in parentFolders]
                            if not args.dry_run and (args.no_confirm or input("Do you want to initiate a search for a season-pack? (y/n): ").lower() == 'y'):
                                results = arr.automaticSearch(media, childId)
                                runAsyncInThread(checkAutomaticSearchStatus(arr, results['id'], media.title, childId))

                                if repairIntervalSeconds > 0:
                                    print(f"Waiting {args.repair_interval} before next repair...")
                                    time.sleep(repairIntervalSeconds)
                            else:
                                print("Skipping")
                            print()

        except Exception:
            e = traceback.format_exc()
            error_msg = f"An error occurred while processing {media.title}: "
            print(error_msg + e)
            discordError(error_msg, e)
            
    if not args.season_packs and seasonPackPendingMessages:
        printSection("Non-season-pack folders")
        print("The following media has non season-pack folders.")
        print("Run the script with --season-packs argument to upgrade to season-pack")
        print()
        for title, childIdFolders in seasonPackPendingMessages.items():
            printSection(f"Non-season-pack folders for {title}", "-")
            for childId, folders in childIdFolders.items():
                if folders:
                    print(f"Season {childId} folders:")
                    print("Inside",'/'.join(folders[0].split('/')[:-1]) + '/')
                    [print('/' + folder.split('/')[-1] + '/') for folder in folders]
                    print()
        printSection("Non-season-pack folders End")

    msg = "Repair complete" + (" with no broken items found" if not fixedBrokenItems else "")
    printSection(msg)
    discordUpdate(msg)

def unsafe():
    return (args.mode == 'symlink' and 
        ((realdebrid['enabled'] and not ensureTuple(validateRealdebridMountTorrentsPath())[0]) or 
        (torbox['enabled'] and not ensureTuple(validateTorboxMountTorrentsPath())[0])))

if runIntervalSeconds > 0:
    while True:
        try:
            main()
            print(f"Waiting for {args.run_interval} before next run...")
            time.sleep(runIntervalSeconds)
        except Exception:
            e = traceback.format_exc()

            error_msg = "An error occurred in the main loop: "
            print(error_msg + e)
            discordError(error_msg, e)
            time.sleep(runIntervalSeconds)  # Still wait before retrying
else:
    main()
