import schedule
import json
import time
import logging
from datetime import datetime
import threading
from src.utils import message_publisher
from src import constant

class Scheduler:
    def __init__(self, play_callback, mqtt_client, 
                config, gpio_control=None,audio=None, 
                state_publisher=None, audio_publisher=None,
                resource_lock=None,call_lock=None,
                emergency_lock=None,current_playing_scheduler=None,realTime_lock=None,schedule_lock=None):
        self.play_callback = play_callback
        self.mqtt = mqtt_client
        self.config = config
        self.gpio = gpio_control
        self.audio=audio
        self.state_publisher = state_publisher
        self.audio_publisher = audio_publisher
        self.playing_schedule=None
        self.jobs = []
        self.executed_jobs = set()
        self.current_playing_scheduler=current_playing_scheduler
        self.resource_lock=resource_lock
        self.call_lock=call_lock
        self.emergency_lock=emergency_lock
        self.realTime_lock=realTime_lock
        self.schedule_lock=schedule_lock

        # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
        #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
    def load_schedule(self):
        try:
            with open(self.config['configSchedulePath'], 'r') as f:
                self.jobs = json.load(f)
                logging.info(f"Loaded {len(self.jobs)} jobs")
        except Exception as e:
            logging.error(f"Failed to load schedule: {e}")
    def run(self):
        while True:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                current_time_str = now.strftime("%H:%M")
                self.load_schedule()
                for job in self.jobs:
                    timeString=""
                    self.current_playing_schedule=[""]
                    schedule_id = job.get('scheduleId')
                    
                    job_key = f"{schedule_id}_{today_str}"

                    if job_key in self.executed_jobs:
                        continue

                    # Kiểm tra ngày
                    if today_str not in job.get('scheduleDates', []):
                        continue

                    # Kiểm tra thời gian
                    job_time = datetime.strptime(job['scheduleTime'], "%H:%M:%S").strftime("%H:%M")
                    if current_time_str != job_time:
                        continue
                    timeString=f"{job['scheduleTime']}_{today_str}"
                    # Đánh dấu đã chạy
                    self.executed_jobs.add(job_key)
                    
                    
                    if not self.emergency_lock.is_set():
                        time.sleep(0.1)
                        logging.info(f"[Scheduler] emergency_lock trong if: {self.emergency_lock}")
                        self.emergency_lock.set()
                    logging.info(f"[Scheduler] emergency_lock: {self.emergency_lock}")
                    #kiem tra xem co cuoc goi dang dien ra hay khong
                    if self.call_lock.is_set() or self.realTime_lock.is_set():
                        message=f"Đã có lịch phát tại {self.audio.station_name} vào lúc {job['scheduleTime']} bị bỏ lỡ"
                        #def publish_message_respond(mqtt, topic,, stationName, type, message,schedule_id=None,status=None):
                        message_publisher.publish_message_respond(mqtt=self.mqtt, 
                            topic=self.config['topics']['respond'], 
                            stationName=self.mqtt.station_name, 
                            type=constant.GENERAL_MESS_TYPE, 
                            message=message)
                        break
                    else:
                        if not self.schedule_lock.is_set():
                            self.schedule_lock.set()
                    # Lấy tham số
                    file_path = job['audioFilePath']
                    record_name = job.get('recordName', 'recorded')
                    repeat_count = job.get('repeatCount', 1)
                    job_type = job.get('type', 1)  # mặc định là 1 (phát + ghi âm)
                    intervalTime=self.config['intervalTime']
                    self.current_playing_schedule[0]=job['scheduleId']
                    logging.info(f"[Scheduler] Chạy job {schedule_id} tại {current_time_str}")
                    with self.resource_lock:
                        if job_type == 1:
                            thread = threading.Thread(
                                target=self.play_with_recording,
                                args=(file_path, record_name, repeat_count, intervalTime,timeString),
                                name="play_with_recording"
                            )
                            thread.start()

                        elif job_type == 0:
                            thread = threading.Thread(
                                target=self.play_only,
                                args=(file_path, repeat_count, intervalTime,timeString),
                                name="play_only"
                            )
                            thread.start()
                    self.current_playing_schedule=[""]
                    if self.schedule_lock.is_set():
                        self.schedule_lock.clear()
                time.sleep(60)
            except Exception as e:
                logging.error(f"[Scheduler.run] Error: {e}")
                time.sleep(5)

    def play_only(self, file_path, repeat_count, intervalTime,timeString):
        if self.audio.playing and self.audio.current_file == file_path:
            logging.warning(f"[play_only] Đang phát file này rồi: {file_path}")
            return

        logging.info(f"[play_only] Bắt đầu phát file: {file_path}")
        self.play_callback(file_path, repeat_count, intervalTime)

    def play_with_recording(self, file_path, record_name, repeat_count, intervalTime,timeString):
        try:
            # Nếu file đang được phát → bỏ qua
            if self.audio.playing and self.audio.current_file == file_path:
                logging.warning(f"Đang phát file này rồi: {file_path}")
                return

            # Mở ampli
            logging.info("🔊 Bật ampli và bắt đầu ghi âm")
            self.gpio.turn_on_amplifier()
            
            # Chỉ cho 1 thread ghi âm tại 1 thời điểm
            #with self.recording_lock:
            try:
                self.audio.start_recording()
            except Exception as e:
                logging.error(f"Recording error: {e}")
                self.gpio.turn_off_amplifier()
                message_publisher.publish_message_respond(mqtt=self.mqtt,
                                    status=constant.ERROR_MESSAGE,
                                    topic=self.config['topics']['respond'],
                                    stationName=self.config['station_name'],
                                    type=constant.GENERAL_MESS_TYPE,
                                    message="Lỗi micro không hoạt động")
                # Tắt ampli nếu lỗi
                return
            if not self.gpio.status_speaker:
                logging.info("✅ amply khong hoat dong.")
                # gpio.turn_off_amplifier()
                self.audio.stop_recording()
                message_publisher.publish_message_respond(mqtt=self.mqtt,
                                    status=constant.ERROR_MESSAGE,
                                    topic=self.config['topics']['respond'],
                                    stationName=self.config['station_name'],
                                    type=constant.GENERAL_MESS_TYPE,
                                    message="Lỗi amply không hoạt động")
                return 
            # Publish trạng thái OK nếu vào được recording

            #Ham lay gia tri status_speaker
            #status_speaker=self.gpio.get_amplifier_status()
            # self.state_publisher.publish_device_status(
            #     self.mqtt, self.config['topics']['statusRespon'],
            #     self.mqtt.station_name, status_speaker, self.audio.recording
            # )
            self.state_publisher.publish_device_status(
                self.mqtt, self.config['topics']['statusRespon'],
                self.mqtt.station_name, 1, self.audio.recording
            )
            self.state_publisher.publish_broadcasting_status(
                self.mqtt, self.config['topics']['broadcastingRespond'],
                self.mqtt.station_name, 1, self.audio.recording
            )
            # Phát file lặp lại theo cấu hình
            #audio.play_newsletter chinh la ham play_callback
            is_succeed=self.play_callback(file_path, repeat_count, intervalTime,timeString)
            # Sau khi phát xong
            if is_succeed:
                logging.info("✅ Phát xong → dừng ghi âm và tắt ampli")
                audio_array = self.audio.stop_recording()

                # Lưu file ghi âm
                try:
                    file_recorded_path = self.audio.save_recording(audio_array, record_name=record_name,save_dir=self.config['scheduleRecordPath'],timeString=timeString)
                except Exception as e:
                    logging.error(f"[Audio] Save recording error: {e}")
                    file_recorded_path = None
                self.gpio.turn_off_amplifier()
                # Gửi file ghi âm nếu có
                if file_recorded_path and self.audio_publisher:
                    self.audio_publisher.publish_audio_recording(
                        self.mqtt, self.config['topics']['sendData'], file_recorded_path
                    )

                # Cập nhật trạng thái hoàn tất
                self.state_publisher.publish_completion_status(
                    self.mqtt, self.config['topics']['completeRespond'],
                    self.mqtt.station_name, 0, self.audio.recording
                )

                logging.info("🎉 Hoàn tất vòng phát + ghi âm")
                if self.schedule_lock.is_set():
                    self.schedule_lock.clear()
        except Exception as e:
            logging.error(f"[play_with_recording] Error: {e}")

