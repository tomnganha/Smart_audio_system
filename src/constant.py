STATUS_READY = 1
STATUS_BROADCASTING = 2
STATUS_DONE = 3
STATUS_WAITING = 0
#call_state
NO_CALL =-1#khong co cuoc goi nao
ACTIVE_CALL=0# dang dam thoai
HELD_CALL=1
DIALING_CALL=2
ALERTING_CALL=3
INCOMING_CALL=4# dang do chuong=> dung chomay ben nhan
WAITING_CALL=5
DISCONNECT=6

#call_type tu hm check_call
VALID_CALL=1# phat hien co cuoc goi den va dung so dien thoai
INVALID_CALL=-1# phat hien co cuoc goi den va ko dung so dien thoai
ERROR_CALL_TYPE =0
RESET_CALL=None

#message type
SCHEDULE_MESS_TYPE="schedule"
GENERAL_MESS_TYPE="general"
#message status
SUCCESS_MESSAGE="SUCCESS"
ERROR_MESSAGE="ERROR"
#configPFolderath
# CONFIG_FOLDER_PATH="/home/admin/Documents/config/"
# #CONFIG_FOLDER_PATH="/home/admin/Documents/new_project/config/"
# CONFIG_ALLOWED_NUMBER_JSON_PATH=f"{CONFIG_FOLDER_PATH}allowed_numbers.json"
# CONFIG_CONFIG_JSON_PATH=f"{CONFIG_FOLDER_PATH}config.json"
# CONFIG_SCHEDULE_JSON_PATH=f"{CONFIG_FOLDER_PATH}schedule.json"
# STATION_CONF_PATH="/etc/station.conf"
