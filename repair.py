import os
import argparse
import asyncio
import time
import traceback
import threading
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

async def check_automatic_search_status(arr, command_id: int, media_title: str, wait_seconds: int = 30, max_attempts: int = 3):
    """
    Check the automatic search status up to max_attempts, waiting wait_seconds between each check.
    Stops early if search_successful is no longer None.
    """
    for attempt in range(0, max_attempts):
        await asyncio.sleep(wait_seconds)
        search_successful, message, exception = arr.checkAutomaticSearchStatus(command_id)

        if search_successful is True:
            success_msg = f"Search for {media_title} succeeded: {message}"
            print(success_msg, level="SUCCESS")
            discordUpdate(success_msg)
            return
        elif search_successful is False:
            error_msg = f"Search for {media_title} failed: {message} {exception}"
            print(error_msg, level="ERROR")
            discordError(error_msg)
            return
    # If we exit the loop, the status was still None after max_attempts
    print(f"Search status for {media_title} still unknown after {max_attempts*wait_seconds} seconds. Not checking anymore.", level="WARNING")
    
def run_async_in_thread(coro):
    """
    Run an async coroutine in a new thread with its own event loop.
    """
    def thread_target():
        # Each thread needs its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
        loop.close()
    
    thread = threading.Thread(target=thread_target)
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
    
def print_section(title: str, char: str = "="):
    """Print a section header."""
    line = char * (len(title) + 4)
    print()
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
    print_section("Starting Repair Process")
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

    season_pack_pending_messages = []
    fixed_broken_items = False
    
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
                    fixed_broken_items = True
                    msg = f"Repairing {media.title} (ID: {childId})"
                    msg2 = f"Found {len(brokenItems)} broken items:"
                    print_section(msg, "-")
                    discordUpdate(msg, msg2)
                    print(msg2)
                    [print(item) for item in brokenItems]
                    print()
                    if args.dry_run or args.no_confirm or input("Do you want to delete and re-grab? (y/n): ").lower() == 'y':
                        if not args.dry_run:
                            if args.mode == 'symlink':
                                print("Deleting broken symlinks...")
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
                            run_async_in_thread(check_automatic_search_status(arr, results['id'], media.title))
                            
                            if repairIntervalSeconds > 0:
                                print(f"Waiting {args.repair_interval} before next repair...")
                                time.sleep(repairIntervalSeconds)
                    else:
                        print("Skipping")
                    print()
                elif args.mode == 'symlink':
                    realPaths = [os.path.realpath(item.path) for item in childItems]
                    parentFolders = set(os.path.dirname(path) for path in realPaths)
                    if childId in media.fullyAvailableChildrenIds and len(parentFolders) > 1:
                        msg = f"{media.title} has {len(parentFolders)} non-season-pack folders.")
                        if args.season_packs:
                            print(msg)
                        else:
                            season_pack_pending_messages.append(msg))
                        if args.season_packs:
                            print("Searching for season-pack")
                            results = arr.automaticSearch(media, childId)
                            run_async_in_thread(check_automatic_search_status(arr, results['id'], media.title))

                            if repairIntervalSeconds > 0:
                                print(f"Waiting {args.repair_interval} before next repair...")
                                time.sleep(repairIntervalSeconds)

        except Exception:
            e = traceback.format_exc()
            error_msg = f"An error occurred while processing {media.title}: "
            print(error_msg + e)
            discordError(error_msg, e)
            
    if not args.season_packs and season_pack_pending_messages:
        print_section("Season Packs Start")
        print("The following media has non season-pack")
        print("Run the script with --season-packs arguemnt to upgrade to season-pack")
        for message in season_pack_pending_messages:
            print(message)
        print_section("Season Packs End")

    msg = "Repair complete" + (" with no broken items found" if not fixed_broken_items else "")
    print_section(msg)
    discordUpdate(msg)

def unsafe():
    return (args.mode == 'symlink' and 
        ((realdebrid['enabled'] and not ensureTuple(validateRealdebridMountTorrentsPath())[0]) or 
        (torbox['enabled'] and not ensureTuple(validateTorboxMountTorrentsPath())[0])))

if runIntervalSeconds > 0:
    while True:
        try:
            main()
            print("Run Interval: Waiting for " + args.run_interval + " before next run...")
            time.sleep(runIntervalSeconds)
        except Exception:
            e = traceback.format_exc()

            error_msg = "An error occurred in the main loop: "
            print(error_msg + e)
            discordError(error_msg, e)
            time.sleep(runIntervalSeconds)  # Still wait before retrying
else:
    main()
