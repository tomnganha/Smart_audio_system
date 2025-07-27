import logging
import json
import time
def publish_device_status(mqtt, topic, station_name, speaker_on, recording):
    data = {
        "stationName": station_name,
        "statusSpeaker": "READY" if speaker_on else "FAIL",
        "statusRecording": "READY" if recording else "FAIL"
    }
    mqtt.publish(topic, json.dumps(data,separators=(",", ":")))
    # mqtt.publish(topic, data)
    logging.info(f"[STATE] Device status: {data}")
    return data


def publish_broadcasting_status(mqtt, topic, station_name, speaker_on, recording):
    data = {
        "stationName": station_name,
        "statusSpeaker": "BROADCASTING" if speaker_on else "FAIL",
        "statusRecording": "BROADCASTING" if recording else "FAIL"
    }
    time.sleep(0.1)
    mqtt.publish(topic, json.dumps(data,separators=(",", ":")))
    # mqtt.publish(topic, data)
    logging.info(f"[STATE] Broadcasting status: {data}")
    return data


def publish_completion_status(mqtt, topic, station_name, speaker_on, recording):
    data = {
        "stationName": station_name,
        "statusSpeaker": "DONE" if not speaker_on else "FAIL",
        "statusRecording": "DONE" if not recording else "FAIL"
    }
    time.sleep(0.1)
    mqtt.publish(topic, json.dumps(data,separators=(",", ":")))
    # mqtt.publish(topic, data)
    logging.info(f"[STATE] Completion status: {data}")
    return data