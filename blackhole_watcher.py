import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from blackhole import on_created, getPath
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from shared.arr import Radarr, Sonarr
from shared.websocket import WebSocketManager
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import requests

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="/app/static", html=True), name="static")

# API routes must come before the catch-all route
@app.get("/api/tmdb/{media_type}/{tmdb_id}/images")
async def get_tmdb_images(media_type: str, tmdb_id: int):
    api_key = os.getenv('TMDB_API_KEY')
    if not api_key:
        print("TMDB_API_KEY not found in environment variables")
        raise HTTPException(status_code=500, detail="TMDB API key not configured")
        
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"TMDB Error Response: {response.text}")
            return {"logo_path": None}
            
        data = response.json()
        
        if 'logos' in data and data['logos']:
            english_logos = [logo for logo in data['logos'] if logo.get('iso_639_1') == 'en']
            if english_logos:
                best_logo = sorted(english_logos, key=lambda x: (x.get('vote_average', 0), x.get('width', 0)), reverse=True)[0]
                return {"logo_path": best_logo['file_path']}
        
        return {"logo_path": None}
    except Exception as e:
        print(f"Error in TMDB API:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Serve index.html for the root route
@app.get("/")
async def read_root():
    return FileResponse("/app/static/index.html")

# Add the arrinfo endpoint before the catch-all route
@app.get("/arrinfo")
async def get_arr_info():
    try:
        # Initialize both Radarr and Sonarr clients
        radarr = Radarr()
        sonarr = Sonarr()
        
        # Get latest movie and series info
        latest_movie = None
        latest_series = None
        
        # Try to get latest movie from Radarr
        try:
            movies = radarr.getMovies()
            if movies:
                latest_movie = max(movies, key=lambda x: x.json.get('added', ''))
                if latest_movie:
                    media_info = latest_movie.json.get('movieFile', {}).get('mediaInfo', {})
                    
                    # Parse audio codec using the new function
                    audio_codec = parse_audio_codec(media_info.get('audioCodec', ''))
                    
                    latest_movie = {
                        "title": latest_movie.title,
                        "year": latest_movie.json.get('year'),
                        "images": [
                            {
                                "coverType": img.get('coverType'),
                                "remoteUrl": img.get('remoteUrl')
                            }
                            for img in latest_movie.json.get('images', [])
                        ],
                        "quality": latest_movie.json.get('movieFile', {}).get('quality', {}).get('quality', {}),
                        "mediaInfo": {
                            "audioCodec": audio_codec.get('audioCodec'),
                            "videoCodec": media_info.get('videoCodec'),
                            "videoDynamicRange": media_info.get('videoDynamicRange'),
                            "audioChannels": media_info.get('audioChannels'),
                            "resolution": media_info.get('resolution')
                        }
                    }
        except Exception as e:
            print(f"Error getting Radarr info: {str(e)}")
            
        # Try to get latest series from Sonarr
        try:
            series = sonarr.getSeries()
            if series:
                latest_series = max(series, key=lambda x: x.json.get('added', ''))
                if latest_series:
                    media_info = latest_series.json.get('episodeFile', {}).get('mediaInfo', {})
                    
                    # Parse audio codec using the new function
                    audio_codec = parse_audio_codec(media_info.get('audioCodec', ''))
                    
                    latest_series = {
                        "title": latest_series.title,
                        "images": [
                            {
                                "coverType": img.get('coverType'),
                                "remoteUrl": img.get('remoteUrl')
                            }
                            for img in latest_series.json.get('images', [])
                        ],
                        "quality": latest_series.json.get('episodeFile', {}).get('quality', {}).get('quality', {}),
                        "mediaInfo": {
                            "audioCodec": audio_codec.get('audioCodec'),
                            "videoCodec": media_info.get('videoCodec'),
                            "videoDynamicRange": media_info.get('videoDynamicRange'),
                            "audioChannels": media_info.get('audioChannels'),
                            "resolution": media_info.get('resolution')
                        }
                    }
        except Exception as e:
            print(f"Error getting Sonarr info: {str(e)}")

        return {
            "movie": latest_movie,
            "series": latest_series
        }
    except Exception as e:
        print(f"Error in get_arr_info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve index.html for any unmatched routes (for client-side routing)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("/app/static/index.html")

class Image(BaseModel):
    coverType: str
    remoteUrl: str

class Quality(BaseModel):
    name: str
    source: str
    resolution: int

class MediaInfo(BaseModel):
    audioCodec: str
    videoCodec: str
    videoDynamicRange: str

class Movie(BaseModel):
    title: str
    year: int
    images: List[Image]
    quality: Optional[Quality]
    mediaInfo: Optional[MediaInfo]

class Series(BaseModel):
    title: str
    seasonNumber: int
    episodeNumbers: List[int]
    images: List[Image]
    quality: Optional[Quality]
    mediaInfo: Optional[MediaInfo]

class ArrInfo(BaseModel):
    movie: Optional[Movie]
    series: Optional[Series]

def parse_audio_codec(audio_codec: str) -> str:
    """Parse audio codec and handle all possible combinations"""
    
    # Normalize the input
    audio_codec = audio_codec.upper() if audio_codec else ''
    
    # Combined format mappings
    combined_formats = {
        ('TRUEHD', 'ATMOS'): 'TrueHD-Atmos',
        ('DTS', 'HD'): 'DTS-HD',
        ('DTS', 'X'): 'DTS-X',
        ('DIGITAL', 'PLUS'): 'DigitalPlus',
        ('EAC3', 'ATMOS'): 'DigitalPlus',  # EAC3 is also known as DD+ or Digital Plus
        ('DD', 'PLUS'): 'DigitalPlus',
        ('AC3', 'PLUS'): 'DigitalPlus',
    }
    
    # Check for combined formats
    for (format1, format2), result in combined_formats.items():
        if format1 in audio_codec and format2 in audio_codec:
            return result
            
    # Single format mappings
    single_formats = {
        'TRUEHD': 'TrueHD',
        'DTS': 'DTS',
        'AC3': 'AC3',
        'AAC': 'AAC',
        'EAC3': 'DigitalPlus',
        'DD': 'AC3',  # Dolby Digital is AC3
    }
    
    # Check for single formats
    for format_key, result in single_formats.items():
        if format_key in audio_codec:
            return result
            
    return audio_codec

def parse_video_format(video_codec: str, dynamic_range: str) -> tuple[str, str]:
    """Parse video codec and dynamic range, handling all combinations"""
    
    # Normalize inputs
    video_codec = video_codec.upper() if video_codec else ''
    dynamic_range = dynamic_range.upper() if dynamic_range else ''
    
    # Dynamic Range mappings
    dynamic_formats = {
        'DOLBY VISION': 'DV',
        'HDR10': 'HDR',
        'HDR10+': 'Plus',
        'HDR': 'HDR',
        'DV': 'DV',
    }
    
    # Find matching dynamic range format
    detected_range = None
    for format_key, result in dynamic_formats.items():
        if format_key in dynamic_range:
            detected_range = result
            break
    
    # Handle combined formats
    combined_format = None
    if detected_range:
        if detected_range == 'DV' and 'HDR' in dynamic_range:
            combined_format = 'DV-HDR'
        elif detected_range == 'DV' and 'PLUS' in dynamic_range:
            combined_format = 'DV-Plus'
    
    # Video codec mappings (if needed for future use)
    video_formats = {
        'X265': 'HEVC',
        'HEVC': 'HEVC',
        'X264': 'AVC',
        'AVC': 'AVC',
        'H264': 'AVC',
        'H.264': 'AVC',
    }
    
    # Find matching video codec
    detected_codec = None
    for format_key, result in video_formats.items():
        if format_key in video_codec:
            detected_codec = result
            break
    
    return detected_codec, combined_format or detected_range

async def parse_media_info(media_info: Dict[str, Any]) -> Dict[str, Any]:
    """Parse media info and return formatted data"""
    audio_codec = parse_audio_codec(media_info.get('audioCodec', ''))
    video_codec, dynamic_range = parse_video_format(
        media_info.get('videoCodec', ''),
        media_info.get('videoDynamicRange', '') or media_info.get('videoDynamicRangeType', '')
    )
    
    return {
        "audioCodec": audio_codec,
        "videoCodec": video_codec,
        "videoDynamicRange": dynamic_range,
        "audioChannels": media_info.get('audioChannels'),
        "resolution": media_info.get('resolution')
    }

async def get_latest_media(client: Any, is_movie: bool) -> Optional[Dict[str, Any]]:
    """Get latest media from Radarr/Sonarr"""
    try:
        items = client.getMovies() if is_movie else client.getSeries()
        if not items:
            return None
            
        latest_item = max(items, key=lambda x: x.json.get('added', ''))
        if not latest_item:
            return None
            
        media_info = (
            latest_item.json.get('movieFile', {}) if is_movie 
            else latest_item.json.get('episodeFile', {})
        ).get('mediaInfo', {})
        
        parsed_media_info = await parse_media_info(media_info)
        
        return {
            "title": latest_item.title,
            "year": latest_item.json.get('year') if is_movie else None,
            "images": [
                {
                    "coverType": img.get('coverType'),
                    "remoteUrl": img.get('remoteUrl')
                }
                for img in latest_item.json.get('images', [])
            ],
            "quality": (
                latest_item.json.get('movieFile', {}) if is_movie 
                else latest_item.json.get('episodeFile', {})
            ).get('quality', {}).get('quality', {}),
            "mediaInfo": parsed_media_info
        }
    except Exception as e:
        print(f"Error getting {'movie' if is_movie else 'series'} info: {str(e)}")
        return None

@app.get("/api/arrinfo")
async def get_arr_info() -> Dict[str, Optional[Dict[str, Any]]]:
    """Get latest media info from both Radarr and Sonarr"""
    try:
        radarr = Radarr()
        sonarr = Sonarr()
        
        latest_movie = await get_latest_media(radarr, is_movie=True)
        latest_series = await get_latest_media(sonarr, is_movie=False)
        
        return {
            "movie": latest_movie,
            "series": latest_series
        }
    except Exception as e:
        print(f"Error in get_arr_info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch media info: {str(e)}"
        )

class BlackholeHandler(FileSystemEventHandler):
    def __init__(self, is_radarr):
        super().__init__()
        self.is_radarr = is_radarr
        self.path_name = getPath(is_radarr, create=True)

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith((".torrent", ".magnet")):
            asyncio.run(on_created(self.is_radarr))

    async def on_run(self):
        await on_created(self.is_radarr)

async def start_application():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    print("Starting blackhole watcher")
    
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
            start_application(),
            radarr_handler.on_run(),
            sonarr_handler.on_run()
        )
    except KeyboardInterrupt:
        radarr_observer.stop()
        sonarr_observer.stop()

    radarr_observer.join()
    sonarr_observer.join()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        await WebSocketManager.get_instance().add_websocket(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                print(f"Received data from {websocket.client}: {data}")
                if data.get('type') == 'ping':
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            await WebSocketManager.get_instance().remove_websocket(websocket)
        except Exception as e:
            WebSocketManager.get_instance().remove_websocket(websocket)
    except Exception as e:
        print(f"Failed to accept WebSocket connection: {e}")

if __name__ == "__main__":
    asyncio.run(main())
