import os
import re
import time
import argparse
from shared.shared import blackhole, realdebrid

parentDirectory = realdebrid['mountTorrentsPath']

def get_completed_parent_directory(use_radarr, use_radarr4k, use_radarranime, use_radarrmux, use_sonarr, use_sonarr4k, use_sonarranime, use_sonarrmux, custom_directory):
    if custom_directory:
        return custom_directory
    elif use_radarr:
        return f"{blackhole['baseWatchPath']}/{blackhole['radarrPath']}/completed"
    elif use_radarr4k:
        return f"{blackhole['baseWatchPath']}/{blackhole['radarrPath']} 4k/completed"
    elif use_radarranime:
        return f"{blackhole['baseWatchPath']}/{blackhole['radarrPath']} anime/completed"
    elif use_radarrmux:
        return f"{blackhole['baseWatchPath']}/{blackhole['radarrPath']} mux/completed"
    elif use_sonarr:
        return f"{blackhole['baseWatchPath']}/{blackhole['sonarrPath']}/completed"
    elif use_sonarr4k:
        return f"{blackhole['baseWatchPath']}/{blackhole['sonarrPath']} 4k/completed"
    elif use_sonarranime:
        return f"{blackhole['baseWatchPath']}/{blackhole['sonarrPath']} anime/completed"
    elif use_sonarrmux:
        return f"{blackhole['baseWatchPath']}/{blackhole['sonarrPath']} mux/completed"
    else:
        return None

def retry_find_directory(directory, max_retries=60, wait_time=1):
    """Retry finding the directory every second for a total of 60 seconds, updating the status message."""
    print("Finding torrents", end="", flush=True)
    for attempt in range(max_retries):
        if os.path.isdir(directory):
            print("\nDirectory found.")
            return True
        print(".", end="", flush=True)
        time.sleep(wait_time)
    print("\nFailed to find directory.")
    return False

def process_directory(directory, completedParentDirectory, custom_regex=None, dry_run=False):
    fullDirectory = os.path.join(parentDirectory, directory)
    completedFullDirectory = os.path.join(completedParentDirectory, directory)

    multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
    multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
    multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'
    if custom_regex:
        multiSeasonRegexCombined += f'|{custom_regex}'

    multiSeasonMatch = re.search(multiSeasonRegexCombined, directory)

    if not retry_find_directory(fullDirectory):
        print(f"Failed to find directory: {fullDirectory} after 60 seconds.")
        return

    # Print the message indicating the directory being processed
    print(f"Symlinks sent to {completedParentDirectory.split('/')[-2]} for {directory}")

    for root, dirs, files in os.walk(fullDirectory):
        relRoot = os.path.relpath(root, fullDirectory)
        for filename in files:
            if multiSeasonMatch:
                seasonMatch = re.search(r'S([\d]{2})E[\d]{2}', filename)
                
                if seasonMatch:
                    season = seasonMatch.group(1)
                    seasonShort = season[1:] if season[0] == '0' else season

                    seasonDirectory = re.sub(multiSeasonRegex1, seasonShort, directory)
                    seasonDirectory = re.sub(multiSeasonRegex2, season, seasonDirectory)
                    if custom_regex:
                        seasonDirectory = re.sub(custom_regex, f' Season {seasonShort} S{season} ', seasonDirectory)

                    completedSeasonFullDirectory = os.path.join(completedParentDirectory, seasonDirectory)

                    if not dry_run:
                        os.makedirs(os.path.join(completedSeasonFullDirectory, relRoot), exist_ok=True)
                        os.symlink(os.path.join(root, filename), os.path.join(completedSeasonFullDirectory, relRoot, filename))
                    continue

            if not dry_run:
                os.makedirs(os.path.join(completedFullDirectory, relRoot), exist_ok=True)
                os.symlink(os.path.join(root, filename), os.path.join(completedFullDirectory, relRoot, filename))

def process(directory, completedParentDirectory, custom_regex, dry_run=False, no_confirm=False):
    if directory:
        process_directory(directory, completedParentDirectory, custom_regex, dry_run)
    else:
        for directory in os.listdir(parentDirectory):
            fullDirectory = os.path.join(parentDirectory, directory)
            if os.path.isdir(fullDirectory):
                if dry_run:
                    print(f"Would process {directory}")
                else:
                    print(f"Processing {directory}...")
                response = input("Do you want to process this directory? (y/n): ") if not no_confirm and not dry_run else 'y'
                if response.lower() == 'y':
                    process_directory(directory, completedParentDirectory, custom_regex, dry_run)
                else:
                    print(f"Skipping processing of {directory}")

def main():
    parser = argparse.ArgumentParser(description='Process directories for torrent imports.')
    parser.add_argument('--directory', type=str, help='Specific directory to process')
    parser.add_argument('--custom-regex', type=str, help='Custom multi-season regex')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation')
    parser.add_argument('--radarr', action='store_true', help='Use the Radarr symlink directory')
    parser.add_argument('--radarr4k', action='store_true', help='Use the Radarr4K symlink directory')
    parser.add_argument('--radarranime', action='store_true', help='Use the RadarrAnime symlink directory')
    parser.add_argument('--radarrmux', action='store_true', help='Use the Radarrmux symlink directory')
    parser.add_argument('--sonarr', action='store_true', help='Use the Sonarr symlink directory')
    parser.add_argument('--sonarr4k', action='store_true', help='Use the Sonarr4K symlink directory')
    parser.add_argument('--sonarranime', action='store_true', help='Use the SonarrAnime symlink directory')
    parser.add_argument('--sonarrmux', action='store_true', help='Use the Sonarrmux symlink directory')
    parser.add_argument('--symlink-directory', type=str, help='Custom symlink directory')
    args = parser.parse_args()

    if args.directory or args.radarr or args.radarr4k or args.radarranime or args.radarrmux or args.sonarr or args.sonarr4k or args.sonarranime or args.sonarrmux or args.symlink_directory:
        # Process once with the provided arguments and exit
        completedParentDirectory = get_completed_parent_directory(
            args.radarr, args.radarr4k, args.radarranime, args.radarrmux,
            args.sonarr, args.sonarr4k, args.sonarranime, args.sonarrmux,
            args.symlink_directory
        )
        if not completedParentDirectory:
            parser.error("One of --radarr, --radarr4k, --radarranime, --sonarr, --sonarr4k, --sonarranime, or --symlink-directory is required.")
        
        process(args.directory, completedParentDirectory, args.custom_regex, args.dry_run, args.no_confirm)
    else:
        # Enter interactive loop for continuous processing
        while True:
            directory = input("Enter the directory to process: ")
            choice = input("Is this for Radarr, Radarr4K, RadarrAnime, Radarrmux, Sonarr, Sonarr4K, or SonarrAnime, Sonarrmux? (r/r4k/ra/rm/s/s4k/sa/sm): ").strip().lower()
            
            radarr, radarr4k, radarranime, radarrmux, sonarr, sonarr4k, sonarranime, sonarrmux = False, False, False, False, False, False, False, False
            
            if choice == 'r':
                radarr = True
            elif choice == 'r4k':
                radarr4k = True
            elif choice == 'ra':
                radarranime = True
            elif choice == 'rm':
                radarrmux = True
            elif choice == 's':
                sonarr = True
            elif choice == 's4k':
                sonarr4k = True
            elif choice == 'sa':
                sonarranime = True
            elif choice == 'sm':
                sonarrmux == True
            else:
                print("Invalid choice. Please try again.")
                continue

            completedParentDirectory = get_completed_parent_directory(
                radarr, radarr4k, radarranime, radarrmux,
                sonarr, sonarr4k, sonarranime, sonarrmux,
                None
            )
            if not completedParentDirectory:
                print("Invalid directory configuration. Please try again.")
                continue

            process(directory, completedParentDirectory, args.custom_regex, args.dry_run, args.no_confirm)

if __name__ == '__main__':
    main()
