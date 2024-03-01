from shared.arr import Arr, Sonarr, Radarr

src_dir = '/path/to/src/'
dst_dir = '/path/to/dst/'

def moveMedia(arr: Arr):
    items = arr.getAll()

    for item in items:
        if item.path.startswith(dst_dir):
            continue

        print(f"Moving {item.title} - {item.size/1073741824}GB")
        item.path = item.path.replace(src_dir, dst_dir)
        arr.put(item)
        break


moveMedia(Sonarr())
moveMedia(Radarr())