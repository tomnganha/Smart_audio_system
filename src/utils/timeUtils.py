from datetime import datetime

def getCurrentTime():
    # Lấy thời gian hiện tại
    currentTime = datetime.now()
    
    # Định dạng thành chuỗi theo yêu cầu
    currentTimeString = currentTime.strftime("%H:%M:%S_%Y-%m-%d")
    
    return currentTimeString

