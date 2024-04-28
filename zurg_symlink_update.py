import os
import json
import argparse

def update_symlink(src_path, new_name, dry_run):
    target_link_path = os.readlink(src_path)
    new_target_path = os.path.join(os.path.dirname(target_link_path), new_name)
    if not dry_run:
        os.unlink(src_path)
        os.symlink(new_target_path, src_path)
    print(f"Updated symlink: {os.path.basename(src_path)} -> {new_name}")

def main(dry_run, no_confirm):
    data_directory = "path/to/zurg/data"
    symlink_directory = "path/to/symlinks"
    switch_to_retain = True

    # Load all symlinks from the symlink directory into memory
    symlink_map = {}
    for root, dirs, files in os.walk(symlink_directory):
        for file in files:
            full_path = os.path.join(root, file)
            if os.path.islink(full_path):
                symlink_map[full_path] = os.readlink(full_path)

    for filename in os.listdir(data_directory):
        file_path = os.path.join(data_directory, filename)
        with open(file_path, 'r') as file:
            data = json.load(file)
            original_name = data['OriginalName']
            current_name = data['Name']
            
            original_name_no_ext = os.path.splitext(original_name)[0]
            
            # Check all symlinks and update if they point to a relevant path
            for symlink_path, target_path in symlink_map.items():
                if switch_to_retain:
                    if target_path.endswith(original_name) or target_path.endswith(original_name_no_ext):
                        if dry_run or no_confirm or input(f"Update symlink for {original_name} to {current_name}? (y/n): ").lower() == 'y':
                            update_symlink(symlink_path, current_name, dry_run)
                else:
                    if target_path.endswith(current_name):
                        if dry_run or no_confirm or input(f"Revert symlink for {current_name} to {original_name}? (y/n): ").lower() == 'y':
                            update_symlink(symlink_path, original_name, dry_run)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update symlinks based on JSON metadata.')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation')
    args = parser.parse_args()

    main(args.dry_run, args.no_confirm)


