import os
import argparse
import shutil
import traceback
from shared.shared import realdebrid

def find_non_linked_files(src_folder, dst_folder, dry_run=False, no_confirm=False, only_delete_files=False):
    # Get the list of links in the dst_folder
    dst_links = set()
    for root, dirs, files in os.walk(dst_folder, followlinks=True):
        for file in files:
            dst_path = os.path.join(root, file)
            if os.path.islink(dst_path):
                dst_links.add(os.path.realpath(dst_path))

    # Check for non-linked files in the src_folder
    for root, dirs, files in os.walk(src_folder, followlinks=True):
        # Get the subdirectory of the current root, relative to the src_folder
        subdirectory = os.path.relpath(root, src_folder)
        subdirectory_any_linked_files = False
        for file in files:
            src_file = os.path.realpath(os.path.join(root, file))

            if src_file in dst_links:
                subdirectory_any_linked_files = True
            # else:
                # print(f"File {src_file} is not used!")
        
        if any(files) and not subdirectory_any_linked_files:
            print(f"Directory {subdirectory} is not used!")
            if not dry_run:
                response = input("Do you want to delete this directory? (y/n): ") if not no_confirm else 'y'
                if response.lower() == 'y':
                    if only_delete_files:
                        try:
                            for file in files:
                                os.remove(os.path.realpath(os.path.join(root, file)))
                            print(f"Files in directory {subdirectory} deleted!")
                        except Exception as e:
                            print(f"Error during file deletion!")
                            print(traceback.format_exc())
                    else:
                        try:
                            shutil.rmtree(os.path.realpath(root))
                            print(f"Directory {subdirectory} deleted!")
                        except Exception as e:
                            print(f"Directory {subdirectory} error during deletion!")
                            print(traceback.format_exc())
                else:
                    print(f"Directory {subdirectory} not deleted!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and delete non-linked file directories.')
    parser.add_argument('dst_folder', type=str, help='Destination folder to check for non-linked files. WARNING: This folder must encompass ALL folders where symlinks may live otherwise folders will unintentionally be deleted')
    parser.add_argument('--src-folder', type=str, default=realdebrid['mountTorrentsPath'], help='Source folder to check for non-linked files')
    parser.add_argument('--dry-run', action='store_true', help='print non-linked file directories without deleting')
    parser.add_argument('--no-confirm', action='store_true', help='delete non-linked file directories without confirmation')
    parser.add_argument('--only-delete-files', action='store_true', help='delete only the files in the non-linked directories')
    args = parser.parse_args()
    find_non_linked_files(args.src_folder, args.dst_folder, dry_run=args.dry_run, no_confirm=args.no_confirm, only_delete_files=args.only_delete_files)
