# config cac gia tri o trang thai cuoc goi gan no thanh hang so
import json
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import os
import base64
from src.gpio_control import GPIOControl
from src.sim7600x import SIM7600X
from src.audio import Audio
from src.mqtt_client import MQTTClient
from src.scheduler import Scheduler
from src.utils import state_publisher
from src.utils import audio_publisher
from src.utils import timeUtils
from src import constant
from src import emergency
from src.utils import message_publisher  # publish_message_respond
from src import constant
from src import cleanup
from queue import Queue
import pygame
import argparse
from config_loader import load_config
from src.utils import initializer


def update_call_event_state(event, should_be_on: bool):
    if should_be_on and not event.is_set():
        event.set()
    elif not should_be_on and event.is_set():
        event.clear()


def handle_call_end(gpio, audio, mqtt, config, call_lock, prev_state, call_state, call_type, timeString):

    if prev_state == constant.ACTIVE_CALL:  # co dam thoai dien ra
        time.sleep(3)
        gpio.turn_off_amplifier()
        audio_array = audio.stop_recording()
        if audio_array is not None and len(audio_array) > 0:
            file_path = audio.save_recording(
                audio_array, record_name="fromCall", save_dir=config['callRecordPath'], timeString=timeString)
            if file_path:
                published = audio_publisher.publish_audio_recording(
                    mqtt, config['topics']['sendData'], file_path)
                if published:
                    status_speaker = gpio.status_speaker
                    # Ham lay gia tri status_speaker
                    # status_speaker=gpio.get_amplifier_status()
                    status_recording = audio.recording
                    state_publisher.publish_completion_status(
                        mqtt, config['topics']['completeRespond'],
                        mqtt.station_name, status_speaker, status_recording
                    )
        update_call_event_state(call_lock, False)
        call_type = constant.RESET_CALL
    elif prev_state == constant.INCOMING_CALL and call_type != constant.INVALID_CALL:  # nha may
        gpio.turn_off_amplifier()
        audio_array = audio.stop_recording()
        # Ham lay gia tri status_speaker
        # status_speaker=gpio.get_amplifier_status()
        status_speaker = gpio.status_speaker
        status_recording = audio.recording
        # if status_speaker:
        state_publisher.publish_completion_status(
            mqtt, config['topics']['completeRespond'],
            mqtt.station_name, status_speaker, status_recording
        )
        update_call_event_state(call_lock, False)
        call_type = constant.RESET_CALL
    call_type = constant.RESET_CALL
    return -1  # cập nhật prev


def handle_ringing(sim, gpio, audio, mqtt, config, call_lock):
    update_call_event_state(call_lock, True)
    if not call_lock.is_set():
        call_lock.set()
    gpio.turn_on_amplifier()
    logging.info("✅ Amplifier đã bật và hoạt động bình thường (có dòng điện).")
    # Ham lay gia tri status_speaker
    status_speaker = gpio.status_speaker
    # status_speaker = 1
    # Ham lay gia tri status_speaker
    # status_recording = audio.recording
    try:
        audio.start_recording()
    except Exception as e:
        logging.error(f"Recording error: {e}")
        # Tắt ampli nếu lỗi
        gpio.turn_off_amplifier()
        sim.hang_up()
        message_publisher.publish_message_respond(mqtt=mqtt,
                                                  status=constant.ERROR_MESSAGE,
                                                  topic=config['topics']['respond'],
                                                  stationName=config['station_name'],
                                                  type=constant.GENERAL_MESS_TYPE,
                                                  message="Lỗi micro không hoạt động")
        update_call_event_state(call_lock, False)
        return
    if not status_speaker:
        gpio.turn_off_amplifier()
        audio.stop_recording()
        sim.hang_up()
        message_publisher.publish_message_respond(mqtt=mqtt,
                                                  status=constant.ERROR_MESSAGE,
                                                  topic=config['topics']['respond'],
                                                  stationName=config['station_name'],
                                                  type=constant.GENERAL_MESS_TYPE,
                                                  message="Lỗi amply không hoạt động")
        update_call_event_state(call_lock, False)
    else:
        state_publisher.publish_device_status(mqtt,
                                              config['topics']['statusRespon'],
                                              mqtt.station_name,
                                              status_speaker, audio.recording)
        time.sleep(1)
        sim.answer_call()


def call_handler(sim, gpio, audio, mqtt, config, resource_lock, call_lock, emergency_lock):
    prev_state = constant.NO_CALL
    timeString = ""
    while True:
        time.sleep(0.2)
        try:
            # kiem tra trang thai cuoc goi: ko co, dang do chuong, dang dam thoai
            call_state = sim.get_call_state()
            call_type = sim.check_call()  # kiem tra co dung so dien thoai hay khong
            if call_type == constant.VALID_CALL:  # co cuoc goi den va dung so dien thoai
                emergency_lock.set()
                if not call_lock.is_set():
                    call_lock.set()
                if call_state == constant.INCOMING_CALL:  # dang do chuong
                    with resource_lock:
                        handle_ringing(sim, gpio, audio, mqtt,
                                       config, call_lock)
                if call_state == constant.ACTIVE_CALL:
                    if prev_state == constant.INCOMING_CALL:
                        update_call_event_state(call_lock, True)
                        # Ham lay gia tri status_speaker
                        # status_speaker=gpio.get_amplifier_status()
                        status_speaker = gpio.status_speaker
                        status_recording = audio.recording
                        state_publisher.publish_broadcasting_status(
                            mqtt, config['topics']['broadcastingRespond'], mqtt.station_name,
                            status_speaker, status_recording
                        )
                        timeString = timeUtils.getCurrentTime()
            elif call_type == constant.INVALID_CALL:  # co so dien thoai la goi den
                with resource_lock:
                    try:
                        sim.hang_up()
                        update_call_event_state(call_lock, False)
                        if emergency_lock.is_set():
                            emergency_lock.clear()
                        call_type = constant.RESET_CALL
                    except Exception as e:
                        logging.error(f"Loi khi cu may: {e}")
            else:  # khong co so dien thoai nao goi den ca
                if call_state == constant.NO_CALL:  # khong co cuoc goi nao den ca
                    if prev_state == constant.ACTIVE_CALL or (prev_state == constant.INCOMING_CALL and call_type != constant.INVALID_CALL):
                        with resource_lock:
                            handle_call_end(
                                gpio, audio, mqtt, config, call_lock, prev_state, call_state, call_type, timeString)
                            timeString = ""
                            if emergency_lock.is_set():
                                emergency_lock.clear()
                    if emergency_lock.is_set():
                        emergency_lock.clear()
            prev_state = call_state
            call_type = constant.RESET_CALL

        except Exception as e:
            logging.error(f"call_handler FAIL: {e}")
            gpio.turn_off_amplifier()
            try:
                audio.start_recording()
            except Exception as e:
                logging.error(f"Recording error: {e}")
            time.sleep(2)


def realtime_audio_handler(audio, mqtt, gpio, resource_lock, call_lock, emergency_lock, realTime_lock, realtime_audio_queue, intervalTime):
    while True:
        try:
            data = realtime_audio_queue.get()  # Chờ vĩnh viễn đến khi có phần tử

            # Nếu đang có cuộc gọi hoặc phát bản tin ưu tiên thì bỏ qua
            if call_lock.is_set():
                logging.info(
                    "⚠️ Đang bận (cuộc gọi hoặc ưu tiên), bỏ qua phát realtime")
                continue
            if not realTime_lock.is_set():
                realTime_lock.set()
            if not realTime_lock.is_set():
                realTime_lock.set()

            file_path = data.get("fileRealTimePath")
            repeat_count = int(data.get("repeatCount", 0))
            timeString = timeUtils.getCurrentTime()
            recordName = data.get('recordName')
            if not file_path or not os.path.exists(file_path):
                logging.warning(f"⚠️ File realtime không tồn tại: {file_path}")
                continue

            with resource_lock:
                realTime_lock.set()

                for i in range(repeat_count + 1):
                    logging.info(
                        f"🔊 Phát realtime {i + 1}/{repeat_count + 1}: {file_path}")
                    if call_lock.is_set():
                        logging.warning(
                            "📞 Ngắt phát hoan toan vì có cuộc gọi đến")
                        break
                    try:
                        pygame.mixer.music.load(file_path)
                        pygame.mixer.music.play()

                        while pygame.mixer.music.get_busy():
                            if call_lock.is_set():
                                logging.warning(
                                    "📞 Ngắt phát vì có cuộc gọi đến")
                                pygame.mixer.music.stop()
                                if realTime_lock.is_set():
                                    realTime_lock.clear()
                                break
                            # if emergency_lock.is_set():
                            #     logging.warning("🚨 Ngắt phát vì có bản tin ưu tiên")
                            #     pygame.mixer.music.stop()
                            #     break
                            time.sleep(0.1)

                        # Nếu bị ngắt thì không phát tiếp
                        if call_lock.is_set():
                            if realTime_lock.is_set():
                                realTime_lock.clear()
                            break

                        # Delay nhẹ trước lần lặp tiếp theo
                        time.sleep(intervalTime)

                    except Exception as e:
                        logging.error(f"‼️ Lỗi khi phát file mp3: {e}")
                        break
                if not call_lock.is_set():
                    gpio.turn_off_amplifier()
                    audio_array = audio.stop_recording()
                    if audio_array is not None and len(audio_array) > 0:
                        file_path = audio.save_recording(
                            audio_array, record_name=recordName, save_dir=mqtt.realTimeRecordPath, timeString=timeString)
                        if file_path:
                            published = audio_publisher.publish_audio_recording(
                                mqtt, mqtt.topics['sendData'], file_path)
                            if published:
                                status_speaker = gpio.status_speaker
                                # Ham lay gia tri status_speaker
                                # status_speaker=gpio.get_amplifier_status()
                                status_recording = audio.recording
                                state_publisher.publish_completion_status(
                                    mqtt, mqtt.topics['completeRespond'],
                                    mqtt.station_name, gpio.status_speaker, status_recording
                                )

                if realTime_lock.is_set():
                    realTime_lock.clear()
        except Exception as e:
            logging.error(f"[RealtimeAudioHandler] Lỗi: {e}")
            time.sleep(1)


def main():
    # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
    #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')

    #########################################################################################

    # Khởi tạo logging với RotatingFileHandler
    os.makedirs("logs", exist_ok=True)

    handler = RotatingFileHandler(
        filename='/project/logs/app.log',  # Vẫn dùng file log cũ
        maxBytes=1_000_000,       # Giới hạn 1MB
        backupCount=3             # Tối đa 3 file log cũ
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Gỡ mọi handler mặc định nếu có (tránh trùng log nếu chạy nhiều lần)
    logger.propagate = False

    # 3

    parser = argparse.ArgumentParser()
    parser.add_argument('--station', required=True, help='Tên trạm cần chạy')
    parser.add_argument('--project_path', required=True,
                        help='Đường dẫn thư mục gốc của dự án')
    args = parser.parse_args()

    # Khoi tao cac thu muc va cac file config neu chung chua co trong du an
    initializer.initialize_project_structure(args.project_path)

    config_path = os.path.join(args.project_path, 'config', 'config.json')
    try:
        config = load_config(
            config_path=config_path,
            station_name=args.station,
            folderProjectPath=args.project_path
        )
    except FileNotFoundError:
        logging.error(
            f"❌ Không tìm thấy file cấu hình tại: {constant.CONFIG_CONFIG_JSON_PATH}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"❌ File cấu hình không đúng định dạng JSON: {e}")
        return
    except Exception as e:
        logging.error(f"❌ Lỗi không xác định khi load config: {e}")
        return

    record_lock = threading.Lock()
    gpio_lock = threading.Lock()
    audio_lock = threading.Lock()
    # Thread lock for shared resources

    resource_lock = threading.Lock()

    call_lock = threading.Event()  # Doc uu tien cao thu 1
    realTime_lock = threading.Event()  # Do uu tien cao thu 2
    schedule_lock = threading.Event()  # Do uu tien cao thu 3

    emergency_lock = threading.Event()  # Doc uu tien cao thu 4

    realtime_audio_queue = Queue()

    current_playing_scheduler = [""]

    # Initialize components
    gpio = GPIOControl(relay_pin=config['gpio']['relay_pin'],
                       ac_Sensor_Relay_COM=config['gpio']['ac_Sensor_Relay_COM'],
                       ac_Sensor_Relay_NO=config['gpio']['ac_Sensor_Relay_NO'],
                       button_pin=config['gpio']['button_pin'],
                       gpio_lock=gpio_lock,
                       emergency_lock=emergency_lock,
                       current_playing_scheduler=current_playing_scheduler,
                       )
    sim = SIM7600X(allowedNumbersPath=config['configAllowedNumbersPath'])

    mqtt = MQTTClient(broker=config['mqtt']['broker'],
                      port=config['mqtt']['port'],
                      username=config['mqtt']['username'],
                      password=config['mqtt']['password'],
                      station_name=config['station_name'],
                      topics=config['topics'],
                      scheduleRecordPath=config['scheduleRecordPath'],
                      scheduleListPath=config['configSchedulePath'],
                      allowed_numbersPath=config['configAllowedNumbersPath'],
                      scheduleAudioPath=config['scheduleAudioPath'],
                      defaultRecordPath=config['defaultRecordPath'],
                      realTimeAudioPAth=config['realTimeAudioPAth'],
                      realTimeRecordPath=config['realTimeRecordPath'],
                      current_playing_scheduler=current_playing_scheduler,
                      emergency_lock=emergency_lock,
                      resource_lock=resource_lock,
                      realTime_lock=realTime_lock,
                      gpio=gpio,
                      sim=sim,
                      realtime_audio_queue=realtime_audio_queue,
                      call_lock=call_lock
                      )
    audio = Audio(sample_rate=48000,
                  mqtt=mqtt,
                  station_name=config['station_name'],
                  callRecordPath=config['callRecordPath'],
                  scheduleRecordPath=config['scheduleRecordPath'],
                  scheduleAudioPath=config['scheduleAudioPath'],
                  audio_lock=audio_lock,
                  record_lock=record_lock,
                  call_lock=call_lock,
                  emergency_lock=emergency_lock,
                  realTime_lock=realTime_lock,
                  schedule_lock=schedule_lock
                  )
    mqtt.set_audio(audio)
    # ftp = FTPClient(config['ftp']['server'], config['ftp']['username'],
    #                 config['ftp']['password'], config['ftp']['path'])

    # Tao scheduler va nap lich
    # def __init__(self, play_callback, mqtt_client, config, gpio_control=None, state_publisher=None, audio_publisher=None):
    scheduler = Scheduler(play_callback=audio.play_newsletter,
                          mqtt_client=mqtt,
                          config=config,
                          gpio_control=gpio,
                          audio=audio,
                          state_publisher=state_publisher,
                          audio_publisher=audio_publisher,
                          resource_lock=resource_lock,
                          call_lock=call_lock,
                          emergency_lock=emergency_lock,
                          current_playing_scheduler=current_playing_scheduler,
                          realTime_lock=realTime_lock,
                          schedule_lock=schedule_lock
                          )

    gpio.add_emergency_callback(lambda: emergency.play_emergancy_announcement(
        audio=audio,
        gpio=gpio,
        emergency_lock=emergency_lock,
        resource_lock=resource_lock,
        schedule_lock=schedule_lock,
        realTime_lock=realTime_lock,
        call_lock=call_lock,
        callHangup=sim.hang_up,
        gpioTurnOnAmply=gpio.turn_on_amplifier,
        gpioTurnOffAmply=gpio.turn_off_amplifier,
        audioStopRecording=audio.stop_recording,
        emergencyPath=config['defaultRecordPath']
    ))
    # thuc hien coa dinh ki voi hai thu muc chua file ghi am tu loa phat thanh, tranh qua bo nho
    folders_to_clean = [
        config['callRecordPath'],
        config['scheduleRecordPath'],
        config['realTimeRecordPath']
    ]
    # scheduler = Scheduler(audio.play_newsletter)
    scheduler.load_schedule()
    # -----------------Thread xu ly cuoc goi tu sim-----------------
    # ─── 8. Khởi chạy threads nền ───────────────────────────────────────────

    threading.Thread(target=scheduler.run,
                     name="SchedulerThread",
                     daemon=True).start()
    threading.Thread(
        target=call_handler,
        args=(sim, gpio, audio, mqtt, config,
              resource_lock, call_lock, emergency_lock),
        name="CallHandlerThread",
        daemon=True
    ).start()
    # Cleanup chạy mỗi config['cleanup']['intervalCleanup'] tiếng, xóa file cũ hơn config['cleanup']['daysOld'] ngày
    cleanup_thread = threading.Thread(
        target=cleanup.cleanup_loop,
        args=(folders_to_clean,),
        kwargs={'interval': config['cleanup']['intervalCleanup'],
                'days_old': config['cleanup']['daysOld']},
        name="CleanupThread",
        daemon=True
    ).start()

    threading.Thread(
        target=realtime_audio_handler,
        args=(audio, mqtt, gpio, resource_lock, call_lock, emergency_lock,
              realTime_lock, mqtt.realtime_audio_queue, config['intervalTime']),
        name="RealtimeAudioThread",
        daemon=True
    ).start()

    # -----------------Thread xu ly cuoc goi tu sim-----------------
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("System shutdown (Ctrl-C)")
    finally:
        # Dọn dẹp GPIO nếu lib của bạn không tự làm
        try:
            gpio.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
