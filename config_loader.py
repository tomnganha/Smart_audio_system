import json

def load_config(config_path='config.json', station_name='default_station',folderProjectPath='/home/admin/Documents'):
    with open(config_path, 'r') as f:
        config_str = f.read()

    config_str = config_str.replace('{{stationName}}', station_name)
    config_str=config_str.replace('{{folderProject}}', folderProjectPath)
    config = json.loads(config_str)
    config['station_name'] = station_name
    return config
