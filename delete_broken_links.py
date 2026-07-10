import os
import argparse
import shutil
from shared.shared import blackhole

def delete_broken_links(dst_folder, mode='folder', dry_run=False, no_confirm=False):
    # Collect deletion targets without modifying the tree during walk
    targets = set()

    for dirpath, dirnames, filenames in os.walk(dst_folder):
        for linkname in filenames + dirnames:
            linkpath = os.path.join(dirpath, linkname)
            if os.path.islink(linkpath):
                try:
                    if not os.path.exists(os.readlink(linkpath)):
                        if mode == 'file':
                            targets.add(linkpath)
                        else:
                            targets.add(dirpath)
                except OSError as e:
                    print(f"Error checking link {linkpath}: {e}")

    removed = 0
    label = 'file' if mode == 'file' else 'directory'
    for target in sorted(targets):
        if dry_run:
            print(f"Would delete {label}: {target}")
            continue

        response = input(f"Do you want to delete {target}? (y/n): ") if not no_confirm else 'y'
        if response.lower() == 'y':
            try:
                print(f"Deleting {label}: {target}")
                if mode == 'file':
                    os.unlink(target)
                else:
                    shutil.rmtree(target)
                removed += 1
            except OSError as e:
                print(f"Error deleting {target}: {e}")
        else:
            print(f"{label.capitalize()} {target} not deleted!")

    if dry_run:
        print(f"Would delete {len(targets)} {label}(s) (dry run)")
    else:
        print(f"Deleted {removed} of {len(targets)} {label}(s)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and delete broken symlinks or their parent directories.')
    parser.add_argument('dst_folder', type=str, nargs='?', default=blackhole['baseWatchPath'], help='Destination folder to check for broken symlinks')
    parser.add_argument('--mode', type=str, choices=['file', 'folder'], default='folder', help='Delete broken symlink files (`file`) or their parent directories (`folder`). Default: folder')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be deleted without deleting')
    parser.add_argument('--no-confirm', action='store_true', help='Delete without confirmation')
    args = parser.parse_args()

    if not args.dst_folder:
        parser.error("dst_folder is required (or set BLACKHOLE_BASE_WATCH_PATH)")

    delete_broken_links(args.dst_folder, mode=args.mode, dry_run=args.dry_run, no_confirm=args.no_confirm)
