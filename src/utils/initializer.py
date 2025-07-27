import os
import json

def initialize_project_structure(project_path):
    # Các thư mục cần tạo
    # VD: /home/admin/Documents/smartBroadcastingProject
    folders = [
        os.path.join(project_path, "config"),
        os.path.join(project_path, "sourceAudio", "callRecord"),
        os.path.join(project_path, "sourceAudio", "defaultAudio"),
        os.path.join(project_path, "sourceAudio", "realTime", "audio"),
        os.path.join(project_path, "sourceAudio", "realTime", "record"),
        os.path.join(project_path, "sourceAudio", "schedule", "audio"),
        os.path.join(project_path, "sourceAudio", "schedule", "record"),
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    # Các file JSON mặc định
    config_files = {
        os.path.join(project_path, "config", "config.json"): {
        "mqtt": {
            "broker": "69a3480fb2dda6df22d8ffdb.s1.eu.hivemq.cloud",
            "port": 8883,
            "username": "smartspeaker",
            "password": "Smartspeaker@123"
        },
        "ftp": {
            "server": "your_server_ip",
            "username": "user",
            "password": "pass",
            "path": "/audio/{{stationName}}/"
        },
        "gpio": {
            "relay_pin": 26,
            "ac_Sensor_Relay_COM": 4,
            "ac_Sensor_Relay_NO": 17,
            "button_pin": 18
        },
        "topics":{
            "statusRespon":"center/broadcasting/status/respond/schedule",
            "broadcastingRespond":"center/broadcasting/respond/schedule",
            "completeRespond":"center/broadcasting/complete/respond/schedule",
            "sendData":"station/audio/upload",
            "getSchedulePrivate":"center/broadcasting/schedule/private/{{stationName}}",
            "getScheduleCommon":"center/broadcasting/schedule/common",
            "scheduleCancel":"center/broadcasting/schedule/cancel",
            "getDefault":"center/broadcasting/default",
            "respond":"center/respond",
            "checkStatusPrivateRealTime":"center/broadcasting/status/check/private/{{stationName}}",
            "getRealTime":"center/broadcasting/private/{{stationName}}",
            "statusResponPrivateRealTime":"center/broadcasting/status/respond/private/{{stationName}}",
            "broadcastingRespondRealTime":"center/broadcasting/respond/private/{{stationName}}",
            "completeRespondRealTime":"center/broadcasting/complete/respond/private/{{stationName}}",
            "checkStatusCommonRealTime":"center/broadcasting/status/check/common",
            "statusResponCommonRealTime":"center/broadcasting/status/respond/common",
            "phoneChange":"center/phone/change",
            "phoneChangeRespond":"center/phone/change/respond",
            "phoneDelete":"center/phone/delete",
            "phoneDeleteRespond":"center/phone/delete/respond",
            "create":"center/station/create",
            "createRespond":"center/station/create/respond"
        },
        "cleanup":{
            "intervalCleanup":86400,
            "daysOld":1
        },
        "apn": "v-internet",
        "station_name": "{{stationName}}",
        "callRecordPath":"{{folderProject}}/sourceAudio/callRecord/",
        "scheduleRecordPath":"{{folderProject}}/sourceAudio/schedule/record/",
        "scheduleAudioPath":"{{folderProject}}/sourceAudio/schedule/audio/",
        "defaultRecordPath":"{{folderProject}}/sourceAudio/defaultAudio/",
        "defaultRecordFilePath":"{{folderProject}}/sourceAudio/defaultAudio/default.mp3",
        "realTimeAudioPAth":"{{folderProject}}/sourceAudio/realTime/audio/",
        "realTimeRecordPath":"{{folderProject}}/sourceAudio/realTime/record/",
        "configAllowedNumbersPath":"{{folderProject}}/config/allowed_numbers.json",
        "configFilePath":"{{folderProject}}/config/config.json",
        "configSchedulePath":"{{folderProject}}/config/schedule.json",
        "intervalTime":5
        },
        os.path.join(project_path, "config", "allowed_numbers.json"): {
            "numbers":[],
            "temp_numbers":[]
        },
        os.path.join(project_path, "config", "schedule.json"): []
    }

    for filepath, default_content in config_files.items():
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump(default_content, f, indent=2)
