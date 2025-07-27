from gpiozero import OutputDevice, Button, DigitalInputDevice, DigitalOutputDevice
import logging
import threading
from src import emergency
import time
#CH1-p25-GPIO26
class GPIOControl:
    def __init__(self, relay_pin, ac_Sensor_Relay_COM,ac_Sensor_Relay_NO, button_pin, gpio_lock,emergency_lock,current_playing_scheduler):
        self.relay = OutputDevice(relay_pin, active_high=False, initial_value=False)
        self.ac_Sensor_Relay_COM = DigitalInputDevice(ac_Sensor_Relay_COM)
        self.ac_Sensor_Relay_NO=DigitalOutputDevice(ac_Sensor_Relay_NO,initial_value=True)
        self.button = Button(button_pin, pull_up=True, bounce_time=0.2)
        self.is_on=False#theo dõi trạng thái relay (đã bật hay chưa).
        self.status_speaker = False # đại diện cho trạng thái hoạt động “thực tế” của ampli
        self.gpio_lock = gpio_lock  # 💡 Thêm lock để thread-safe
        self.emergency_lock=emergency_lock
        self.current_playing_scheduler=current_playing_scheduler
        self.is_Playing_emergency=False
        # logging.basicConfig(filename='logs/app.log', level=logging.INFO,
        #                     format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
    def turn_on_amplifier(self):
        with self.gpio_lock:
            if self.is_on:
                return None
            self.relay.on()
            logging.info(f"✅ Amplifier chua bật và self.ac_Sensor_Relay_COM.value = {self.ac_Sensor_Relay_COM.value}")
            time.sleep(2.5)  # ⏱️ Chờ ampli khởi động và cảm biến dòng ổn định
            logging.info(f"✅ Amplifier đã bật và self.ac_Sensor_Relay_COM.value = {self.ac_Sensor_Relay_COM.value}")
            #if self.ac_Sensor_Relay_COM.value == 1:  # 0 = có dòng điện → ampli OK
            if 1: # Mac finh la bat thanh cong, chua ket nnoi voi AC_sensor_relay
                self.status_speaker = True
                self.is_on = True
                logging.info("✅ Amplifier đã bật và hoạt động bình thường (có dòng điện).")
            else:
                self.relay.off()
                self.status_speaker = False
                self.is_on = False
                logging.warning("❌ Amplifier bật thất bại: không phát hiện dòng điện.")
            

    def turn_off_amplifier(self):
        with self.gpio_lock:
            if not self.is_on:
                return None
            
            self.relay.off()
            self.status_speaker = False
            self.is_on=False
            logging.info("Amplifier turned OFF")

    def get_amplifier_status(self):
        return self.ac_Sensor_Relay_COM.value  # 1 nếu có tín hiệu, 0 nếu không

    def add_emergency_callback(self, callback):
        if not self.emergency_lock.is_set() and not self.current_playing_scheduler[0] and (not self.is_Playing_emergency):
            self.button.when_pressed = callback
        # self.button.when_pressed = lambda: play_priority_announcement(audio, emergency_lock, resource_lock)
