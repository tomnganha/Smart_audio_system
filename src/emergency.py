import threading
import time 
import os
def play_emergancy_announcement(audio,gpio, emergency_lock, 
                                resource_lock, 
                                call_lock,
                                schedule_lock,
                                realTime_lock,
                                callHangup,
                                gpioTurnOnAmply,
                                gpioTurnOffAmply,
                                audioStopRecording,
                                emergencyPath):
   
    if schedule_lock.is_set() or call_lock.is_set() or realTime_lock.is_set() or gpio.is_Playing_emergency:
        print("🔁 Đang co ưu tiên rồi hoac dang phat mac dinh, bỏ qua")
        return

    def _play():
        gpioTurnOnAmply()
        with resource_lock:
            try:
                if (not schedule_lock.is_set()) and  ( not call_lock.is_set()) and ( not realTime_lock.is_set()) and ( not gpio.is_Playing_emergency):
                    time.sleep(1)
                    gpio.is_Playing_emergency=True
                    files = [f for f in os.listdir(emergencyPath) if f.endswith(".mp3")]
                    if not files:
                        print("Không tìm thấy file trong thư mục")
                        return
                    file_path = os.path.join(emergencyPath, files[0])
                    #audio.stop_all_playback()  # Hàm này bạn cần có trong Audio
                    # audio.play_audio_file(emergencyPath=file_path,
                    #                     emergency_lock=emergency_lock, 
                    #                     call_lock=call_lock, 
                    #                     realTime_lock=realTime_lock,
                    #                     schedule_lock=schedule_lock)
                    audio.play_audio_file(emergencyPath=file_path,emergency_lock=emergency_lock,
                                            call_lock=call_lock, realTime_lock=realTime_lock, schedule_lock=schedule_lock)
                    # gpio.is_Playing_emergency=False
                else:
                    gpio.is_Playing_emergency=False
                    
                    return 
            except Exception as e:
                print(f"‼️ Lỗi khi phát ưu tiên: {e}")
        #emergency_lock.clear()
        #them logic tat amply

        if (not schedule_lock.is_set()) and  ( not call_lock.is_set()) and ( not realTime_lock.is_set()) and gpio.is_Playing_emergency:
            gpioTurnOffAmply()
            gpio.is_Playing_emergency=False

    threading.Thread(target=_play, name="PriorityAudioThread").start()
