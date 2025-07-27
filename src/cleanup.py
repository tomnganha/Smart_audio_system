import os
import time
import logging

def is_file_old(file_path, days_old):
    """Kiểm tra file có cũ hơn số ngày cho phép không"""
    now = time.time()
    file_mtime = os.path.getmtime(file_path)
    return (now - file_mtime) > (days_old * 86400)

def is_file_being_used(file_path):
    """Kiểm tra file có thể đang bị sử dụng không (bằng cách mở exclusive)"""
    try:
        with open(file_path, 'a'):
            return False
    except IOError:
        return True

def delete_old_files_safe(folder_path, days_old=7):
    if not os.path.exists(folder_path):
        logging.warning(f"Folder does not exist: {folder_path}")
        return

    deleted = 0
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(('.wav', '.mp3')):  # chỉ xóa audio
            continue

        file_path = os.path.join(folder_path, filename)

        if os.path.isfile(file_path):
            try:
                if is_file_old(file_path, days_old) and not is_file_being_used(file_path):
                    os.remove(file_path)
                    logging.info(f"🗑️ Deleted old file: {file_path}")
                    deleted += 1
            except Exception as e:
                logging.error(f"❌ Error deleting file {file_path}: {e}")
    if deleted > 0:
        logging.info(f"✅ Cleanup: Deleted {deleted} file(s) in {folder_path}")

def cleanup_loop(folders, interval, days_old):
    logging.info(f"✅ Cleanup: thuc hien quet va xoa nhung file ghi am cu")
    while True:
        for folder in folders:
            delete_old_files_safe(folder, days_old)
        time.sleep(interval)
