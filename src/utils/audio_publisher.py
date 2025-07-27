# src/utils/audio_publisher.py
import os
import base64
import logging
import json
def publish_audio_recording(mqtt, topic, file_path):
    try:
        filename = os.path.splitext(os.path.basename(file_path))[0]
        with open(file_path, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        data = {
            "recordName": filename,
            "audioBase64": audio_base64
        }
        mqtt.publish(topic, json.dumps(data,separators=(",", ":")))
        # mqtt.publish(topic, data)
        logging.info(f"[AUDIO] Published file: {filename}")
        return True
    except Exception as e:
        logging.error(f"[AUDIO] Failed to publish: {e}")
        return False
