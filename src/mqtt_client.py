import paho.mqtt.client as mqtt
import json
import logging
import time
import ssl
import re
import unicodedata
import os
import base64
from src.utils import saveFileName
import glob
from src.utils import message_publisher
from src import constant
from src.utils import audioUtils
from src.utils import state_publisher

class MQTTClient:
    def __init__(self, broker, port, username, 
                password, 
                station_name,
                topics,
                scheduleRecordPath,
                scheduleListPath,
                allowed_numbersPath,
                scheduleAudioPath,
                defaultRecordPath,
                realTimeAudioPAth,
                realTimeRecordPath,
                current_playing_scheduler,
                emergency_lock,
                resource_lock,
                realTime_lock,
                gpio,sim,
                realtime_audio_queue,
                call_lock
                ):

        self.station_name = station_name
        self.topics=topics
        self.scheduleRecordPath=scheduleRecordPath
        self.scheduleListPath=scheduleListPath
        self.allowed_numbersPath=allowed_numbersPath
        self.scheduleAudioPath=scheduleAudioPath
        self.defaultRecordPath=defaultRecordPath
        self.realTimeAudioPAth=realTimeAudioPAth
        self.realTimeRecordPath=realTimeRecordPath
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.current_playing_scheduler=current_playing_scheduler
        self.emergency_lock=emergency_lock
        self.resource_lock=resource_lock
        self.realTime_lock=realTime_lock
        self.gpio=gpio
        self.sim=sim
        self.audio=None
        self.realtime_audio_queue = realtime_audio_queue
        self.call_lock=call_lock

        # self.jobs=[]

        # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
        #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
        try:
            self.client.connect(broker, port)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"MQTT connection error: {e}")
    # def load_schedule(self):
    #     try:
    #         with open('config/schedule.json', 'r') as f:
    #             self.jobs = json.load(f)
    #             logging.info(f"Loaded {len(self.jobs)} jobs")
    #     except Exception as e:
    #         logging.error(f"Failed to load schedule: {e}")
    def set_audio(self,audio_obj):
        self.audio=audio_obj
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # self.client.subscribe(f"a")
            for topic in self.topics.values():
                self.subscribe_topic(topic)
                
            logging.info("Connected to MQTT broker")
        else:
            logging.error(f"MQTT connection failed, rc={rc}")

    def subscribe_topic(self, topic):
        try:
            self.client.subscribe(topic)
            logging.info(f"Subscribed to topic: {topic}")
        except Exception as e:
            logging.error(f"Failed to subscribe to {topic}: {e}")

    ##############################################

    def handlePayloadSchedule(self, payload):
            # Tạo tên file từ recordName và scheduleId
            record_name = saveFileName.safe_filename(payload['recordName'])
            schedule_id = payload['scheduleId']
            file_name = f"{record_name}_{schedule_id}.mp3"
            file_path = os.path.join(self.scheduleAudioPath, file_name)
            # Giải mã base64 và lưu file MP3
            respond={
                "scheduleId":schedule_id,
                "status":"",
                "message":""
            }
            try:
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(payload['base64AudioFile']))
                
                # return respond
            except Exception as e:
                respond['status']=constant.ERROR_MESSAGE
                respond['message']="Lưu schedule thất bại"
                return respond
                #return  # Dừng hàm nếu lưu không thành công

            # Cập nhật payload
            payload['audioFilePath'] = file_path
            payload['recordName'] = record_name
            del payload['base64AudioFile']
            if "stationName" in payload:
                del payload['stationName']

            # Đọc file JSON hiện có nếu tồn tại
            if os.path.exists(self.scheduleListPath):
                try:
                    with open(self.scheduleListPath, "r", encoding="utf-8") as f:
                        schedule_list = json.load(f)
                except json.JSONDecodeError:
                    schedule_list = []
                    
                except Exception as e:
                    respond['status']=constant.ERROR_MESSAGE
                    respond['message']="Lưu schedule thất bại"
                    return respond
            else:
                schedule_list = []

            # Thêm dữ liệu mới vào danh sách
            schedule_list.append(payload)

            # Ghi lại danh sách vào file JSON
            try:
                with open(self.scheduleListPath, "w", encoding="utf-8") as f:
                    json.dump(schedule_list, f, ensure_ascii=False, indent=2)
                respond['status']=constant.SUCCESS_MESSAGE
                respond['message']="Lưu schedule thành công"
                return respond
            except Exception as e:
                respond['status']=constant.ERROR_MESSAGE
                respond['message']="Lưu schedule thất bại"
                return respond

    def handlePayloadDefault(self, payload):
        if not self.emergency_lock.is_set():
            self.emergency_lock.set()
        respond={
            "status":"",
            "message":""
        }
        # --- Bước 1: Xóa tất cả các file cũ trong defaultRecordPath ---
        for old_file in glob.glob(os.path.join(self.defaultRecordPath, "*.mp3")):
            try:
                os.remove(old_file)
            except Exception as e:
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Lưu bản tin mặc định thất bại, lỗi khi xóa bản tin cũ"
                return respond

        # --- Bước 2: Lưu bản tin mới ---
        try:
            record_name = saveFileName.safe_filename(payload['recordName'])  # Đảm bảo tên file an toàn
            file_name = f"{record_name}_default.mp3"
            file_path = os.path.join(self.defaultRecordPath, file_name)

            # Giải mã base64 và lưu file
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(payload['base64AudioFile']))
            respond["status"]=constant.SUCCESS_MESSAGE
            respond["message"]="Lưu bản tin mặc định thành công"
            return respond
        except Exception as e:
            respond['status']=constant.ERROR_MESSAGE
            respond['message']="Lỗi khi lưu bản tin mặc định"
            return respond

    def handlePayloadCancel(self, payload):
        
        try:
            
            # Nếu payload là chuỗi JSON, parse nó
            if isinstance(payload, str):
                payload = json.loads(payload)

            scheduleIdCancel = payload.get("scheduleId")
            stationName=payload.get("stationName")
            
            respond={
                "status":"",
                "message":"",
                "scheduleId":scheduleIdCancel
            }



            if not scheduleIdCancel:
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Xóa schedule thất bại. Không tìm thấy file lưu trữ"
                return respond
            
            if self.current_playing_scheduler[0]==scheduleIdCancel:
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Xóa schedule thất bại.Schedule đang phát không thể xóa"
                return respond
            # Dùng đường dẫn từ biến self
            scheduleListPath = self.scheduleListPath

            if not os.path.exists(scheduleListPath):
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Xóa schedule thất bại. Không tìm thấy file lưu trữ"
                return respond

            with open(scheduleListPath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError("Dữ liệu trong file không phải là danh sách")
                except Exception as e:
                    respond["status"]=constant.ERROR_MESSAGE
                    respond["message"]="Xóa schedule thất bại. Lỗi đọc file lưu trữ"
                    return respond

            # Xử lý xóa scheduleId
            before_len = len(data)
            new_data = [item for item in data if item.get("scheduleId") != scheduleIdCancel]
            after_len = len(new_data)

            if before_len == after_len:
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Xóa schedule thất bại. Không tìm thấy schedule trong bộ nhớ của trạm"
                return respond

            # Ghi dữ liệu mới vào file
            with open(scheduleListPath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)

            respond["status"]=constant.SUCCESS_MESSAGE
            respond["message"]="Xóa schedule thành công"
            #def cancel_audio_or_recording(identifier, dir_path):# identifier co the la chuoi thoi gian hay scheduleId
            respondCancel=audioUtils.cancel_audio_or_recording(scheduleIdCancel,self.scheduleAudioPath)
            return respond

        except Exception as e:
            respond["status"]=constant.ERROR_MESSAGE
            respond["message"]="Xóa schedule thất bại, lỗi bất định"
            return respond






    ######################################

    def handlePayLoadRealTime(self,payload):

        #"recordName" : "<tên file audio>",
        #"base64AudioFile" : "<base 64 encode>",
        #"repeatCount" : "<số lần lặp (nếu người dùng không chọn lặp thì mặc định repeatCount bằng 0)>"

        if not self.emergency_lock.is_set():
            self.emergency_lock.set()
        respond={
            "status":"",
            "message":"",
            "recordName":payload['recordName'],
            "fileRealTimePath":""
        }
        # --- Bước 1: Xóa tất cả các file cũ trong defaultRecordPath ---
        for old_file in glob.glob(os.path.join(self.realTimeAudioPAth, "*.mp3")):
            try:
                os.remove(old_file)
            except Exception as e:
                respond["status"]=constant.ERROR_MESSAGE
                respond["message"]="Lưu bản tin realTime thất bại, lỗi khi xóa bản tin realTime cũ"
                return respond

        # --- Bước 2: Lưu bản tin mới ---
        try:
            record_name = saveFileName.safe_filename(payload['recordName'])  # Đảm bảo tên file an toàn
            file_name = f"{record_name}.mp3"
            file_path = os.path.join(self.realTimeAudioPAth, file_name)

            # Giải mã base64 và lưu file
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(payload['base64AudioFile']))
            respond["status"]=constant.SUCCESS_MESSAGE
            respond["message"]="Lưu bản tin realTime thành công"
            respond['fileRealTimePath']=file_path
            return respond
        except Exception as e:
            respond['status']=constant.ERROR_MESSAGE
            respond['message']="Lỗi khi lưu ban tin realTime mặc định"
            return respond

    

    def handleChangeNumbers(self,new_numbers,stationName,allowed_numbersPath):
        """Ghi đè danh sách temp_numbers trong file JSON bằng new_numbers."""
        respond={
            "stationName":stationName,
            "status":"",

        }
        if not isinstance(new_numbers, list):
            logging.info("❌ Dữ liệu truyền vào phải là list.")
            respond['status']=constant.ERROR_MESSAGE
            return respond

        for number in new_numbers:
            if not isinstance(number, str):
                logging.info(f"⚠️ Số không hợp lệ: {number} (không phải string)")
                respond['status']=constant.ERROR_MESSAGE
                return respond

        try:
            with open(allowed_numbersPath, "r") as f:
                
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Nếu file không tồn tại hoặc lỗi JSON, khởi tạo mới
            respond['status']=constant.ERROR_MESSAGE
            return respond
        data["temp_numbers"] = new_numbers
        with open(allowed_numbersPath, "w") as f:
            json.dump(data, f, indent=2)

        respond['status']=constant.SUCCESS_MESSAGE
        return respond

    def confirmChangeNumbers(self,allowed_numbersPath):
        try:
            with open(allowed_numbersPath, "r") as f:
                
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Nếu file không tồn tại hoặc lỗi JSON, khởi tạo mới
            return None
        
        data["numbers"] = data['temp_numbers']
        with open(allowed_numbersPath, "w") as f:
            json.dump(data, f, indent=2)

        return data['numbers']

    def on_message(self, client, userdata, msg):
        #nhan data tu server chi co thong tin ve lich phat
        try:
            payload = json.loads(msg.payload.decode())
            if msg.topic==self.topics['getSchedulePrivate']:
                respond=self.handlePayloadSchedule(payload)
                #publish_message_respond(mqtt, topic, stationName, type, message,scheduleId=None,status=None)
                
                
                message_publisher.publish_message_respond(
                    self,
                    self.topics['respond'],
                    stationName=self.station_name,
                    type=constant.SCHEDULE_MESS_TYPE,
                    status=respond['status'],
                    scheduleId=respond['scheduleId'],
                    message=respond['message']
                    )
                
                logging.info(f"Received from {msg.topic}: {payload}")
            elif msg.topic==self.topics['getScheduleCommon']:
                if self.station_name in payload['stationName']:
                    respond=self.handlePayloadSchedule(payload)
                    message_publisher.publish_message_respond(
                        self,
                        self.topics['respond'],
                        stationName=self.station_name,
                        type=constant.SCHEDULE_MESS_TYPE,
                        status=respond['status'],
                        scheduleId=respond['scheduleId'],
                        message=respond['message']
                        )

                    logging.info(f"Received from {msg.topic}: {payload}")
                else:
                    logging.info(f"schedule ko phai cua {self.station_name}")
            elif msg.topic==self.topics['getDefault']:
                if self.station_name in payload['stationName']:
                    respond=self.handlePayloadDefault(payload)
                    message_publisher.publish_message_respond(
                        self,
                        self.topics['respond'],
                        stationName=self.station_name,
                        type=constant.GENERAL_MESS_TYPE,
                        status=respond['status'],
                        message=respond['message']
                        )
                    logging.info(f"Received from {msg.topic}: {payload}")
                else:
                    logging.info(f"schedule ko phai cua {self.station_name}")
            elif msg.topic==self.topics['scheduleCancel']:
                if self.station_name in payload['stationName']:
                    respond=self.handlePayloadCancel(payload)

                    message_publisher.publish_message_respond(
                        self,
                        self.topics['respond'],
                        scheduleId=respond['scheduleId'],
                        stationName=self.station_name,
                        type=constant.SCHEDULE_MESS_TYPE,
                        status=respond['status'],
                        message=respond['message']
                        )
                    logging.info(f"Received from {msg.topic}: {payload}")
                
                else:
                    logging.info(f"schedule ko phai cua {self.station_name}")
            elif msg.topic==self.topics['checkStatusPrivateRealTime']:# Private:lang nghe leng kiem tra status truoc khi phat realtime
                    logging.info(f"Nhan lenh check status")
                    if payload['instruction']=='STATUS_CHECK':
                        #call_lock
                        if not self.call_lock.is_set():
                            if not self.emergency_lock.is_set():
                                    self.emergency_lock.set()
                            if not self.realTime_lock.is_set():#khi dang thao tac voi realtime, set = True
                                    self.realTime_lock.set()
                            with self.resource_lock:
                                self.gpio.turn_on_amplifier()
                                self.audio.start_recording()
                                #def publish_device_status(mqtt, topic, station_name, speaker_on, recording):
                                state_publisher.publish_device_status(
                                    mqtt=self,
                                    topic=self.topics['statusResponPrivateRealTime'],
                                    station_name=self.station_name,
                                    speaker_on=self.gpio.status_speaker,
                                    recording=self.audio.recording
                                )
                                self.emergency_lock.clear()
                                self.realTime_lock.clear()
                        else:
                            logging.info(f"self.call_lock.is_set(): {self.call_lock.is_set()}")
                            logging.info("Co cuoc goi dang dien ra khong the phat realtime")
                            return
                        #Thuc hien cac logic : mo amply, mo mic, va pulish tran gthai READY
                        #gui trang thai status
            elif msg.topic==self.topics['getRealTime']:
                # :lang ngha ban tin khi san sang phat realtime cho tram 1
                logging.info(f"gui trang thai broadcasting RealTime len server")
                if not self.call_lock.is_set():
                    if not self.realTime_lock.is_set():
                        self.realTime_lock.set()
                    with self.resource_lock:
                        if not self.emergency_lock.is_set():# set de rang buoc cho emergency
                            self.emergency_lock.set()
                        if not self.realTime_lock.is_set():#khi dang thao tac voi realtime, set = True
                            self.realTime_lock.set()
                        ####################RUT NGAN THOI GIAN THUC TE NEN XOA DOAN CODE NAY DI
                        self.gpio.turn_on_amplifier()
                        self.audio.start_recording()
                        ####################RUT NGAN THOI GIAN THUC TE NEN XOA DOAN CODE NAY DI
                        state_publisher.publish_broadcasting_status(
                                    mqtt=self,
                                    topic=self.topics['broadcastingRespondRealTime'],
                                    station_name=self.station_name,
                                    speaker_on=self.gpio.status_speaker,
                                    recording=self.audio.recording
                                )
                        respond=self.handlePayLoadRealTime(payload)
                        # ✅ Chỉnh sửa payload
                        payload.pop("base64AudioFile", None)
                        payload["fileRealTimePath"] = respond['fileRealTimePath']
                        # ✅ Đưa vào queue
                        self.realtime_audio_queue.put(payload)
                        logging.info(f"📥 Đã thêm vào realtime_audio_queue: {payload}")
                        #self.realtime_audio_queue.put(payload)
                        if self.realTime_lock.is_set():
                            self.realTime_lock.clear()
                        #tien hanh handle payload, luu file mp3, phat, gui trang thai status
                else:
                    logging.info("Co cuoc goi dang dien ra khong the phat truc tiep")
                    self.gpio.turn_off_amplifier()
                    self.audio.stop_recording()
            elif msg.topic==self.topics['checkStatusCommonRealTime']:
                # :lang nghe lenh kiem tra status common, neu co tram minh thi phan hoi trang thai
                # "stationName" : "<Một list các tên trạm>"
	            # "instruction" : "STATUS_CHECK"
                logging.info("Da co mess gui len realtime check common")
                if self.station_name in payload['stationName']:
                    if payload['instruction']=='STATUS_CHECK':
                        if not self.call_lock.is_set():
                            
                            with self.resource_lock:
                                if not self.emergency_lock.is_set():# set de rang buoc cho emergency
                                    self.emergency_lock.set()
                                if not self.realTime_lock.is_set():#khi dang thao tac voi realtime, set = True
                                    self.realTime_lock.set()
                                self.gpio.turn_on_amplifier()
                                self.audio.start_recording()
                                #def publish_device_status(mqtt, topic, station_name, speaker_on, recording):
                                state_publisher.publish_device_status(
                                    mqtt=self,
                                    topic=self.topics['statusResponCommonRealTime'],
                                    station_name=self.station_name,
                                    speaker_on=self.gpio.status_speaker,
                                    recording=self.audio.recording
                                )
                                self.emergency_lock.clear()
                                self.realTime_lock.clear()
                    logging.info(f"Received from {msg.topic}: {payload}")
                else:
                    logging.info(f"schedule ko phai cua {self.station_name}")
            elif msg.topic==self.topics['phoneChange']:
                if payload.get("listNumbers") is not None:
                    listNumbers=payload['listNumbers']
                    logging.info("Nhan yeu cau thay doi so dien thoai")
                    respond=self.handleChangeNumbers(listNumbers,self.station_name,self.allowed_numbersPath)
                    #gui phan hoi len mqtt
                    self.publish(topic=self.topics['phoneChangeRespond'],data=respond)
                if payload.get("confirmChangeNumber") is not None:
                    confirm=payload['confirmChangeNumber']
                    if confirm==constant.SUCCESS_MESSAGE:
                        new_list=self.confirmChangeNumbers(self.allowed_numbersPath)
                        if new_list is not None:
                            if not self.call_lock.is_set():
                                self.sim.allowed_numbers=new_list
                    else:
                        logging.info("server xac nhan khong thay doi phone numbers")
            elif msg.topic==self.topics['phoneDelete']:
                if payload.get("listNumbers") is not None:
                    listNumbers=payload['listNumbers']
                    logging.info("Nhan yeu cau thay doi so dien thoai")
                    respond=self.handleChangeNumbers(listNumbers,self.station_name,self.allowed_numbersPath)
                    #gui phan hoi len mqtt
                    self.publish(topic=self.topics['phoneDeleteRespond'],data=respond)
                if payload.get("confirmChangeNumber") is not None:
                    confirm=payload['confirmChangeNumber']
                    if confirm==constant.SUCCESS_MESSAGE:
                        new_list=self.confirmChangeNumbers(self.allowed_numbersPath)
                        if new_list is not None:
                            if not self.call_lock.is_set():
                                self.sim.allowed_numbers=new_list
                    else:
                        logging.info("server xac nhan khong thay doi phone numbers")
            elif msg.topic==self.topics['create']:
                stationNameCreate=payload.get('stationName')
                logging.info(f"{self.station_name} duoc he thong khoi tao")
                if stationNameCreate is not None:
                    if stationNameCreate ==self.station_name:
                        data={
                            "stationName":self.station_name,
                            "status": constant.SUCCESS_MESSAGE
                            }
                        self.publish(topic=self.topics['createRespond'],data=data)
                        logging.info(f"{self.station_name} da duoc tao thanh cong, san sang hoat dong")
            elif msg.topic==self.topics['respond']:
                logging.info(f"Khong xu ly message nhan tu center/respond")
        except Exception as e:
            logging.error(f"MQTT message error: {e}")
    def publish(self, topic ,data):
        try:
            payload = json.dumps(data,separators=(",", ":"))
            self.client.publish(topic, payload)
            logging.info(f"Published to {topic}: data")
        except Exception as e:
            logging.error(f"Failed to publish to {topic}: {e}")