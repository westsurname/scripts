
import os
import re
import json
import tempfile
import requests
from flask import Flask, render_template_string, abort, request, Response
from shared.shared import realdebrid

data_directory = '../zurg/data'
symlink_directory = 'somepath'


app = Flask(__name__)
result = {}

def process_json_files_and_symlinks(data_dir, symlink_dir):
    temp_file_path = os.path.join(tempfile.gettempdir(), 'symlink_map.json')

    if os.path.exists(temp_file_path):
        print(f"Loading symlink map from {temp_file_path}")
        with open(temp_file_path, 'r') as temp_file:
            symlink_map = json.load(temp_file)
    else:
        print(f"Creating symlink map and saving to {temp_file_path}")
        symlink_map = {}
        for root, dirs, files in os.walk(symlink_dir):
            for file in files:
                full_path = os.path.join(root, file)
                if os.path.islink(full_path):
                    symlink_map[full_path] = os.readlink(full_path)
                    print(f"Found symlink: {full_path} -> {symlink_map[full_path]}")
        with open(temp_file_path, 'w') as temp_file:
            json.dump(symlink_map, temp_file)
            print(f"Symlink map saved to {temp_file_path}")

    # Loop over the files in the data directory, taking only the first 10 .json files for now
    for filename in os.listdir(data_dir)[:10]:
        if filename.endswith('.json'):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                original_name = data.get('OriginalName')
                files = []
                for selected_file, file_info in data.get('SelectedFiles', {}).items():
                    file_id = file_info.get('id')
                    file_path = file_info.get('path')
                    file_link = file_info.get('Link')

                    # Check all symlinks and add to result if they point to a relevant path
                    for symlink_path, target_path in symlink_map.items():
                        if file_path in target_path:
                            files.append((file_link, symlink_path))
                            # break

                result[original_name] = files


@app.route('/files')
def serve_dirs():
    links = [f'<li><a href="files/{name}">{name}</a></li>' for name in result.keys()]
    return render_template_string(f'<ol>{"".join(links)}</ol>')

@app.route('/files/<path:path>')
def serve_dir(path=''):
    files_with_links = result.get(path, [])
    print(files_with_links)
    if files_with_links:
        transcoded_links = []
        for link, symlink_path in files_with_links:
            unrestrict_url = f"{realdebrid['host']}/unrestrict/link?auth_token={realdebrid['apiKey']}"
            print(link)
            response = requests.post(unrestrict_url, data={'link': link})
            print(response)
            if response.status_code == 200:
                id = response.json().get('id')
                print(id)
                media_infos_url = f"{realdebrid['host']}/streaming/mediaInfos/{id}?auth_token={realdebrid['apiKey']}"
                media_infos_response = requests.get(media_infos_url)
                print(media_infos_response)
                if media_infos_response.status_code == 200:
                    media_infos = media_infos_response.json()
                    print(media_infos)
                    details = media_infos.get('details', {})
                    video_details = details.get('video', {})
                    audio_details = details.get('audio', {})
                    subtitles_details = details.get('subtitles', [])
                    model_url = media_infos.get('modelUrl')
                    available_formats = media_infos.get('availableFormats', {})
                    available_qualities = media_infos.get('availableQualities', {})
                    bitrate = media_infos.get('bitrate', 0)  # Get the bitrate from media info

                    for audio_key, audio_info in audio_details.items():
                        print('audio_key', audio_key)
                        audio_lang = audio_info.get('lang_iso', 'und')
                        audio_codec = audio_info.get('codec', 'Unknown')
                        for subtitle in subtitles_details + [{'lang_iso': 'none'}]:
                            print('subtitle', subtitle)
                            subtitle_lang = subtitle.get('lang_iso', 'none')
                            for quality_key, quality_value in available_qualities.items():
                                print('quality_key', quality_key)
                                for format_key, format_value in available_formats.items():
                                    print('format_key', format_key)
                                    stream_url = model_url.format(
                                        audio=audio_key,
                                        subtitles=subtitle_lang,
                                        audioCodec=audio_codec,
                                        quality=quality_value,
                                        format=format_value
                                    )
                                    transcoded_links.append(f'<li><a href="/proxy?url={stream_url}&bitrate={bitrate}">{os.path.basename(symlink_path)} [Audio Language: {audio_lang}, Subtitle Language: {subtitle_lang}, Audio Codec: {audio_codec}, Quality: {quality_key}, Format: {format_key}]</a></li>')
    if not transcoded_links:
        return abort(404)
    return render_template_string(f'<ol>{"".join(transcoded_links)}</ol>')
@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    print(f"Received URL: {url}")
    bitrate = int(request.args.get('bitrate', 0))
    print(f"Received bitrate: {bitrate}")
    range_header = request.headers.get('Range')
    print(f"Received Range header: {range_header}")
    
    if range_header and bitrate > 0:
        range_match = re.match(r'bytes=(\d+)-', range_header)
        if range_match:
            start_byte = int(range_match.group(1))
            print(f"Start byte: {start_byte}")
            timestamp = start_byte * 8 // bitrate  # Convert bytes to bits and then to seconds
            print(f"Calculated timestamp: {timestamp}")
            url = f"{url}&t={timestamp}"
            print(f"Modified URL: {url}")
    
    response = requests.get(url, stream=True)
    print(f"Response status code: {response.status_code}")
    headers = [(name, value) for name, value in response.raw.headers.items()]
    print(f"Response headers: {headers}")
    return Response(response.iter_content(chunk_size=8192), headers=headers)

if __name__ == '__main__':
    process_json_files_and_symlinks(data_directory, symlink_directory)
    print('Run app')
    app.run(host='0.0.0.0', port=9998)

