#!/bin/bash

STATION_NAME=$1
PROJECT_PATH=$2

if [ -z "$STATION_NAME" ] || [ -z "$PROJECT_PATH" ]; then
    echo "❌ Thiếu tên trạm hoặc đường dẫn dự án!"
    echo "🔧 Cách dùng: ./start_speaker.sh <station_name> <project_path>"
    exit 1
fi

# Đường dẫn tới virtualenv
VENV_PATH="$PROJECT_PATH/project/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Không tìm thấy môi trường ảo tại $VENV_PATH"
    exit 1
fi

echo "🚀 Đang khởi chạy trạm '$STATION_NAME' với dự án tại: $PROJECT_PATH"
source "$VENV_PATH/bin/activate"

python "$PROJECT_PATH/project/main.py" \
    --station "$STATION_NAME" \
    --project_path "$PROJECT_PATH"

