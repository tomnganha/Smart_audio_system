import logging
import json


def publish_message_respond(mqtt, topic, stationName, type, message,scheduleId=None,status=None):
    if scheduleId:#dung cho truong dat lich thanh cong hay that bai
        data = {
        "status":status,
        "stationName": stationName,
        "type": type,
        "scheduleId": scheduleId,
        "message": f"{stationName}: {message}"
        }
    else:
        data = {
        "status":status,
        "stationName": stationName,
        "type": type,
        "message": f"{stationName}: {message}"
        }
    mqtt.publish(topic, json.dumps(data, ensure_ascii=False,separators=(",", ":")))
    logging.info(f"[STATE] Device status: {data}")
    return data