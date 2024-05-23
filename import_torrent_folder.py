import os
import re
import argparse
from shared.shared import blackhole, realdebrid

parentDirectory = realdebrid['mountTorrentsPath']

def get_completed_parent_directory(args):
    if args.symlink_directory:
        return args.symlink_directory
    elif args.radarr:
        return f"{blackhole['baseWatchPath']}/{blackhole['radarrPath']}/completed"
    elif args.sonarr:
        return f"{blackhole['baseWatchPath']}/{blackhole['sonarrPath']}/completed"
    else:
        return

def process_directory(directory, completedParentDirectory, custom_regex=None, dry_run=False):
    fullDirectory = os.path.join(parentDirectory, directory)
    completedFullDirectory = os.path.join(completedParentDirectory, directory)

    multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
    multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
    multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'
    if custom_regex:
        multiSeasonRegexCombined += f'|{custom_regex}'

    multiSeasonMatch = re.search(multiSeasonRegexCombined, directory)

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
                    print('Season Recursive:', f"{os.path.join(completedSeasonFullDirectory, relRoot, filename)} -> {os.path.join(root, filename)}")

                    continue

            if not dry_run:
                os.makedirs(os.path.join(completedFullDirectory, relRoot), exist_ok=True)
                os.symlink(os.path.join(root, filename), os.path.join(completedFullDirectory, relRoot, filename))
            print('Recursive:', f"{os.path.join(completedFullDirectory, relRoot, filename)} -> {os.path.join(root, filename)}")

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process directories for torrent imports.')
    parser.add_argument('--directory', type=str, help='Specific directory to process')
    parser.add_argument('--custom-regex', type=str, help='Custom multi-season regex')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation')
    parser.add_argument('--radarr', action='store_true', help='Use the Radarr symlink directory')
    parser.add_argument('--sonarr', action='store_true', help='Use the Sonarr symlink directory')
    parser.add_argument('--symlink-directory', type=str, help='Custom symlink directory')
    args = parser.parse_args()

    completedParentDirectory = get_completed_parent_directory(args)
    if not completedParentDirectory:
        parser.error("One of --radarr, --sonarr, or --symlink-directory is required.")

    process(args.directory, completedParentDirectory, args.custom_regex, args.dry_run, args.no_confirm)

