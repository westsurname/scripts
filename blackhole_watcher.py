import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from blackhole import on_created, getPath

class BlackholeHandler(FileSystemEventHandler):
    def __init__(self, is_radarr):
        super().__init__()
        self.is_radarr = is_radarr
        self.path_name = getPath(is_radarr, create=True)

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith((".torrent", ".magnet", ".nzb")):
            asyncio.run(on_created(self.is_radarr))

    async def on_run(self):
        await on_created(self.is_radarr)

async def main():
        print("Watching blackhole")

        radarr_handler = BlackholeHandler(is_radarr=True)
        sonarr_handler = BlackholeHandler(is_radarr=False)

        radarr_observer = Observer()
        radarr_observer.schedule(radarr_handler, radarr_handler.path_name)

        sonarr_observer = Observer()
        sonarr_observer.schedule(sonarr_handler, sonarr_handler.path_name)

        try:
            radarr_observer.start()
            sonarr_observer.start()
            
            await asyncio.gather(
                radarr_handler.on_run(),
                sonarr_handler.on_run()
            )
        except KeyboardInterrupt:
            radarr_observer.stop()
            sonarr_observer.stop()

        radarr_observer.join()
        sonarr_observer.join()


if __name__ == "__main__":
    asyncio.run(main())