import sounddevice as sd
import numpy as np
import scipy.io.wavfile
from datetime import datetime
import os
import logging
import subprocess
import shutil 
import pygame
import time
import sys
import threading
# file audio.py hoặc audio_manager.py
from threading import Lock
from src.utils import timeUtils
from src.utils import message_publisher
from src import constant

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


class Audio:
    def __init__(self,mqtt, sample_rate, station_name, callRecordPath, scheduleRecordPath,scheduleAudioPath,audio_lock,record_lock,call_lock,emergency_lock,realTime_lock,schedule_lock):
        self.sample_rate = sample_rate
        self.mqtt=mqtt
        self.station_name = station_name
        self.callRecordPath = callRecordPath
        self.scheduleRecordPath=scheduleRecordPath
        self.scheduleAudioPath=scheduleAudioPath
        self.recording = False
        self.audio_lock=audio_lock#dung cho viec phat thanh len loa
        self.record_lock=record_lock#dung cho viec ghi am
        self.call_lock=call_lock
        self.playing = False
        self.current_file = None
        self.audio_array=[]
        self.currently_playing = set()         # Lưu các file đang phát
        self.lock = threading.Lock() 
        self.emergency_lock=emergency_lock          # Tránh xung đột giữa các thread dùng chung mixer
        self.realTime_lock=realTime_lock
        self.schedule_lock=schedule_lock

        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"‼️ Lỗi khởi tạo pygame.mixer: {e}")


        os.makedirs('logs', exist_ok=True)
        # os.makedirs('audio/temp', exist_ok=True)

        # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
        #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')

    def get_device_index_by_name(self,name):
        for i, dev in enumerate(sd.query_devices()):
            if name in dev['name'] and dev['max_input_channels'] > 0:
                return i
        return None

    def start_recording(self):
        with self.record_lock:
            if self.recording:
                return None
            #self.audio_array=[]
            self.recording = True
            self.audio_data = []
            def callback(indata, frames, time, status):
                if status:
                    logging.warning(f"Stream status: {status}")
                if self.recording:
                    self.audio_data.append(indata.copy())

            try:
                # ✅ Dùng tên thiết bị cụ thể thay vì index (ổn định hơn)
                device_name = 'USB PnP Sound Device'
                device_index = self.get_device_index_by_name("USB PnP Sound Device")
                if device_index is None:
                    logging.error("Không tìm thấy mic USB PnP Sound Device.")
                    return

                # sd.default.device = device_index
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    callback=callback,
                    device=device_name,
                    dtype='int16'     # phù hợp scipy.io.wavfile
                )
                self.stream.start()
                logging.info("Started recording")
            except Exception as e:
                logging.error(f"Recording error: {e}")
                self.recording = False
                


    def stop_recording(self):

        with self.record_lock:
            if not self.recording:
                return None

            try:
                self.stream.stop()
                self.stream.close()
                self.recording = False

                if not self.audio_data:
                    logging.warning("No audio data recorded")
                    return None

                audio_array = np.concatenate(self.audio_data, axis=0)
                logging.info(f"Stop recording")
                return audio_array

            except Exception as e:
                logging.error(f"Stop recording error: {e}")
                return None

    def save_recording(self, audio_array, record_name="fromCall", save_dir=None,timeString=None):
        try:
            # Dùng đường dẫn mặc định nếu không truyền
            if save_dir is None:
                save_dir = self.callRecordPath

            # Tạo thư mục nếu chưa có
            os.makedirs(save_dir, exist_ok=True)

            filename = f"SmartSpeaker_{record_name}_{self.station_name}_{timeString}.mp3"
            mp3_path = os.path.join(save_dir, filename)
            wav_path = mp3_path.replace('.mp3', '.wav')
            # Ghi file WAV
            scipy.io.wavfile.write(wav_path, self.sample_rate, audio_array)
            # Chuyển WAV -> MP3
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', wav_path, mp3_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                logging.error(f"[Audio] ffmpeg conversion failed: {result.stderr.decode()}")
                return None
            # Xóa file WAV gốc
            os.remove(wav_path)
            logging.info(f"[Audio] Saved recording to: {mp3_path}")
            return mp3_path

        except Exception as e:
            logging.error(f"[Audio] Save recording error: {e}")
            return None

    def play_newsletter(self, file, repeats,intervalTime,timeString=None):
        with self.audio_lock:
            # if self.emergency_lock and self.emergency_lock.is_set():
            #     logging.info("⛔ Bỏ qua phát bản tin vì đang phát bản tin ưu tiên")
            #     return 0
            if self.emergency_lock and (not self.emergency_lock.is_set()):
                self.emergency_lock.set()
            ############3#######
            if not os.path.exists(file):
                logging.error(f"File không tồn tại: {file}")
                return
            if file in self.currently_playing:
                logging.warning(f"Đang phát file này rồi: {file}")
                return
            self.currently_playing.add(file)
            self.playing = True
            self.current_file = file
            try:
                interval_seconds = intervalTime
                if interval_seconds is None:
                    logging.error("Interval type không hợp lệ")
                    return
                with self.lock:
                    pygame.mixer.init()
                total_plays = repeats + 1
                for i in range(total_plays):
                    if self.call_lock.is_set() or self.realTime_lock.is_set():
                        timeString=timeString.split("_")[0]
                        message=f"Đã có lịch phát tại {self.station_name} vào lúc {timeString} bị bỏ lỡ"
                        message_publisher.publish_message_respond(
                            mqtt=self.mqtt, 
                            topic=self.mqtt.topics['respond'], 
                            stationName=self.station_name, 
                            type=constant.GENERAL_MESS_TYPE, 
                            message=message)
                        logging.info("📞 Dừng han toan bo phát bản tin vì có cuộc gọi đến hoac phat realTime")
                        return 0
                    else:
                        if not self.schedule_lock.is_set():
                            self.schedule_lock.set()
                    logging.info(f"🎵 Phát file: {file} (lần {i+1}/{total_plays})")
                    with self.lock:
                        pygame.mixer.music.load(file)
                        pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        #Kiem tra xem co cuoc goi den hay khong
                        if self.call_lock.is_set() or self.realTime_lock.is_set():
                            timeString=timeString.split("_")[0]
                            message=f"Đã có lịch phát tại {self.station_name} vào lúc {timeString} bị bỏ lỡ"
                            #def publish_message_respond(mqtt, topic,, stationName, type, message,schedule_id=None,status=None):
                            message_publisher.publish_message_respond(
                                mqtt=self.mqtt, 
                                topic=self.mqtt.topics['respond'], 
                                stationName=self.station_name, 
                                type=constant.GENERAL_MESS_TYPE, 
                                message=message)
                            logging.info("📞 Ngắt phát giữa chừng vì có cuộc gọi")
                            with self.lock:
                                pygame.mixer.music.stop()
                            return 0
                        else:
                            if not self.schedule_lock.is_set():
                                schedule_lock.set()
                        #kiem tra xem co ban tin uu tien duoc phat khong
                        # if self.emergency_lock and self.emergency_lock.is_set():
                        #     logging.info("⛔ Ngắt phát giữa chừng vì có bản tin ưu tiên")
                        #     with self.lock:
                        #         pygame.mixer.music.stop()
                        #     return 0
                        if self.emergency_lock and (not self.emergency_lock.is_set()):
                            self.emergency_lock.set()
                        time.sleep(0.1)
                    if i < total_plays - 1:
                        logging.info(f"⏳ Chờ {interval_seconds}s trước lần tiếp theo")
                        time.sleep(interval_seconds)
                return 1
            except Exception as e:
                logging.error(f"Error khi phát {file}: {e}")
            finally:
                self.playing = False
                self.current_file = None
                self.currently_playing.discard(file)

    def stop_all_playback(self):
        with self.audio_lock:
            pygame.mixer.music.stop()

    def play_audio_file(self, emergencyPath,emergency_lock,call_lock,realTime_lock,schedule_lock):
        with self.audio_lock:
            pygame.mixer.music.load(emergencyPath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                # if self.schedule_lock.is_set() or self.call_lock.is_set() or self.realTime_lock.is_set():
                if schedule_lock.is_set() or call_lock.is_set() or realTime_lock.is_set():
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)




