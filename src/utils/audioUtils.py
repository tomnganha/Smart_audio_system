import os
import logging


#message type
SCHEDULE_MESS_TYPE="schedule"
GENERAL_MESS_TYPE="general"
#message status
SUCCESS_MESSAGE="SUCCESS"
ERROR_MESSAGE="ERROR"


def cancel_audio_or_recording(identifier, dir_path):# identifier co the la chuoi thoi gian hay scheduleId
    respond = {
        "status": "",
        "message": ""
    }
    try:
        if not os.path.exists(dir_path):
            respond['status'] = ERROR_MESSAGE
            respond['message'] = f"Thư mục không tồn tại: {dir_path}"
            return respond

        matched_files = [f for f in os.listdir(dir_path) if f.endswith(".mp3") and identifier in f]

        if not matched_files:
            respond['status'] = ERROR_MESSAGE
            respond['message'] = f"Không tìm thấy file audio duoc luu tru"
            return respond

        for file in matched_files:
            file_path = os.path.join(dir_path, file)
            try:
                os.remove(file_path)
                logging.info(f"[File] Đã xóa file: {file_path}")
            except Exception as e:
                logging.error(f"[File] Lỗi khi xóa file {file_path}: {e}")
                respond['status'] = ERROR_MESSAGE
                respond['message'] = f"Lỗi khi xóa file: {file}"
                return respond

        respond['status'] = SUCCESS_MESSAGE
        respond['message'] =" Da xoa file thanh cong"
        return respond

    except Exception as e:
        logging.error(f"[File] Lỗi không xác định: {e}")
        respond['status'] = ERROR_MESSAGE
        respond['message'] = f"Xoa file audio that bai: {str(e)}"
        return respond
