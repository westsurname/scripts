import os
import json
import tempfile
from flask import Flask, jsonify, send_file, abort

app = Flask(__name__)
result = []

def process_json_files_and_symlinks(data_dir, symlink_dir):
    temp_file_path = os.path.join(tempfile.gettempdir(), 'symlink_map.json')

    if os.path.exists(temp_file_path):
        with open(temp_file_path, 'r') as temp_file:
            symlink_map = json.load(temp_file)
    else:
        symlink_map = {}
        for root, dirs, files in os.walk(symlink_dir):
            for file in files:
                full_path = os.path.join(root, file)
                if os.path.islink(full_path):
                    symlink_map[full_path] = os.readlink(full_path)
        with open(temp_file_path, 'w') as temp_file:
            json.dump(symlink_map, temp_file)

    # Loop over the files in the data directory
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                original_name = data.get('OriginalName')
                for selected_file, file_info in data.get('SelectedFiles', {}).items():
                    file_id = file_info.get('id')
                    file_path = file_info.get('path')
                    file_link = file_info.get('Link')

                    # Check all symlinks and add to result if they point to a relevant path
                    for symlink_path, target_path in symlink_map.items():
                        if original_name in target_path or file_path in target_path:
                            result.append((file_link, symlink_path))

        # TODO: Remove
        break

@app.route('/media/<path:symlink_path>', methods=['GET'])
def serve_file(symlink_path):
    for file_link, symlink in result:
        if symlink == symlink_path:
            return send_file(file_link)
    abort(404)

@app.route('/media', methods=['GET'])
def list_files():
    return jsonify(result)

if __name__ == '__main__':
    data_directory = '../zurg/data'
    symlink_directory = 'somepath'
    process_json_files_and_symlinks(data_directory, symlink_directory)
    app.run(host='0.0.0.0', port=9998)
