import serial
import time
import json
import logging
from src import constant
import os
class SIM7600X:
    def __init__(self,allowedNumbersPath, port="/dev/ttyUSB2", baudrate=115200):
        # self.ser = serial.Serial(port, baudrate, timeout=1)
        

        #Lay cac so dien thoai co trong file config
        self.allowedNumbersPath=allowedNumbersPath
        self.allowed_numbers = self.load_allowed_numbers()
        # self.call_active = False
        # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
        #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')

        if not os.path.exists(port):
            logging.error(f"❌ Port {port} không tồn tại. Kiểm tra lại kết nối USB.")
            raise RuntimeError(f"Port {port} không tồn tại")

        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            logging.info(f"✅ Đã kết nối tới cổng {port}")
        except serial.SerialException as e:
            logging.error(f"❌ Không thể mở port {port}: {e}")
            raise RuntimeError(f"Lỗi khi mở cổng serial: {e}")
        except OSError as e:
            logging.error(f"❌ Lỗi hệ thống khi mở port {port}: {e}")
            raise RuntimeError(f"Lỗi hệ thống: {e}")





    def load_allowed_numbers(self):
        try:
            with open(self.allowedNumbersPath, 'r') as f:
                readed_data=json.load(f)
                return readed_data['numbers']
        except Exception as e:
            logging.error(f"Failed to load allowed numbers: {e}")
            return []
    # ham check_call duoc goi lie tuc de lang nghe cuoc goi, neu co cuo goi thi kt so dth, dung thi tra ve true con khong thi tra ve false
    def check_call(self):# kiem tra neu dung so dien thoai hay khong, neu dung tra ve true, neu sai tra ve false
        try:
            self.ser.write(b'AT+CLCC\r')
            time.sleep(0.5)
            # response = self.ser.read(1000).decode()
            response = self.ser.read_all().decode(errors='ignore')
            for line in response.splitlines():
                if "+CLCC:" in line:
                    parts = line.split(',')
                    if len(parts) >= 5:
                        number = parts[5].strip('"') if len(parts) >= 6 else None
                        if number in self.allowed_numbers:
                            return 1
                        else:# co so goi den nhung khong dung so dien thoai cho phep, tat ngay lap tuc
                            # self.hang_up()
                            return -1

        except serial.SerialException as e:
            logging.error(f"Serial error: {e}")
            # return False
            return 0

    #tao mot ham kiem tra trang thai cuoc goi: co 3 trang thai chinh
    #dang do chuong
    # dang dam thoai
#     Giá trị state	Ý nghĩa
# 0	Đang kết nối (active)=> dangf dam thoai
# 1	Đang giữ (held)
# 2	Đang quay số (dialing)
# 3	Chuông đang phát (alerting)=> dung cho ben may goi
# 4	Có cuộc gọi đến (incoming) => dung cho ben may nhan
# 5	Cuộc gọi đang chờ (waiting)
# 6	Ngắt kết nối (disconnect)
    def get_call_state(self):
        try:
            self.ser.write(b'AT+CLCC\r')
            time.sleep(0.5)
            response = self.ser.read_all().decode(errors='ignore')

            for line in response.splitlines():
                if "+CLCC:" in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        state = int(parts[2])  # Lấy trạng thái cuộc gọi
                        return state  # Chỉ lấy trạng thái đầu tiên

            return -1  # Không có cuộc gọi nào

        except Exception as e:
            logging.error(f"Lỗi khi lấy trạng thái cuộc gọi: {e}")
            return -1

    def extract_caller_id(self, response):#lay so dien thoai khi nhan cuoc goi tra ve so dang string
        for line in response.split('\n'):
            if "+CLCC" in line:
                parts = line.split(',')
                if len(parts) > 5:
                    return parts[5].strip('"')
        return ""
    def answer_call(self):
        try:
            self.ser.write(b'ATA\r')  # Nhấc máy
            time.sleep(1)
            # self.ser.write(b'AT+CMIC=0,10\r')  # Tăng mic
            # self.ser.write(b'AT+CSDVC=3\r')   # Chuyển sang loa ngoài
            logging.info("✅ Đã nhấc máy")
            # self.call_active = True
        except Exception as e:
            logging.error(f"Lỗi khi nhấc máy: {e}")
    
    def hang_up(self):
        try:
            self.ser.write(b'AT+CHUP\r')  # Ngắt cuộc gọi
            time.sleep(1)
            logging.info("📴 Đã kết thúc cuộc gọi")
            # self.call_active = False
        except Exception as e:
            logging.error(f"Lỗi khi kết thúc cuộc gọi: {e}")

