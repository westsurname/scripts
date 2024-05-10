import os
import json
import argparse

data_directory = "/path/to/zurg/data"
symlink_directory = "/path/to/symlinks"
switch_to_retain = True

def update_symlink(src_path, new_name, dry_run):
    target_link_path = os.readlink(src_path)
    path_parts = os.path.split(os.path.dirname(target_link_path))
    new_target_path = os.path.join(os.path.join(*path_parts[:-1]), new_name, os.path.basename(target_link_path))
    if not dry_run:
        os.unlink(src_path)
        os.symlink(new_target_path, src_path)
    print(f"Updated symlink: {os.path.basename(src_path)} -> {new_name}")

def main(dry_run, no_confirm):
    print("Loading symlinks")
    # Load all symlinks from the symlink directory into memory
    symlink_map = {}
    for root, dirs, files in os.walk(symlink_directory):
        for file in files:
            full_path = os.path.join(root, file)
            if os.path.islink(full_path):
                symlink_map[full_path] = os.readlink(full_path)

    print("Loading symlinks complete")

    for filename in os.listdir(data_directory):
        file_path = os.path.join(data_directory, filename)
        with open(file_path, 'r') as file:
            data = json.load(file)
            original_name = data.get('OriginalName')
            current_name = data.get('Name')
            
            if not original_name or not current_name:
                print(f"Skipping {original_name or current_name}")
                continue
            
            original_name_no_ext = os.path.splitext(original_name)[0]
            # Check all symlinks and update if they point to a relevant path
            for symlink_path, target_path in symlink_map.items():
                target_dir_name = os.path.basename(os.path.dirname(target_path))
                if switch_to_retain:
                    if (target_dir_name == original_name or target_dir_name == original_name_no_ext) and target_dir_name != current_name:
                        if dry_run or no_confirm or input(f"Update symlink for {os.path.basename(symlink_path)} from {original_name} to {current_name}? (y/n): ").lower() == 'y':
                            update_symlink(symlink_path, current_name, dry_run)
                    else:
                        print(f"Skipping {target_dir_name}")
                else:
                    if target_dir_name == current_name and target_dir_name != original_name:
                        if dry_run or no_confirm or input(f"Revert symlink for {os.path.basename(symlink_path)} from {current_name} to {original_name}? (y/n): ").lower() == 'y':
                            update_symlink(symlink_path, original_name, dry_run)
                    else:
                        print(f"Skipping {target_dir_name}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update symlinks using Zurg data folder.')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--no-confirm', action='store_true', help='Execute without confirmation')
    args = parser.parse_args()

    main(args.dry_run, args.no_confirm)


