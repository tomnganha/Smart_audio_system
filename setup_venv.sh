#!/bin/bash

# Lấy đường dẫn dự án từ tham số dòng lệnh
PROJECT_DIR=$1

if [ -z "$PROJECT_DIR" ]; then
    echo "❌ Thiếu đường dẫn thư mục dự án!"
    echo "🔧 Cách dùng: ./setup_venv.sh /duong/dan/den/du_an"
    exit 1
fi

VENV_DIR="$PROJECT_DIR/project/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/project/requirements.txt"

# Kiểm tra tồn tại file requirements.txt
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "❌ Không tìm thấy file requirements.txt tại $REQUIREMENTS_FILE"
    exit 1
fi

echo "📦 Đang tạo môi trường ảo tại: $VENV_DIR"
python3 -m venv "$VENV_DIR"

echo "⚙️  Kích hoạt môi trường ảo..."
source "$VENV_DIR/bin/activate"

echo "⬇️ Đang cài đặt các thư viện từ requirements.txt..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"

echo "✅ Hoàn tất thiết lập môi trường ảo cho dự án tại: $PROJECT_DIR"
