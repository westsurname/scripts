import os

def find_broken_links(root):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        for linkname in filenames + dirnames:
            linkpath = os.path.join(dirpath, linkname)
            if os.path.islink(linkpath) and not os.path.exists(os.readlink(linkpath)):
                print(f"{linkpath} is a broken link!")
                count += 1
    print(count)

root_dir = "/path/to/symlinks/dir"
find_broken_links(root_dir)