# utils/filename_utils.py

import unicodedata
import re

def safe_filename(name):
    """
    Chuyển chuỗi có dấu và ký tự đặc biệt thành tên file không dấu, viết hoa đầu từ.
    Ví dụ: 'Bản tin chiều' → 'BanTinChieu'
    """
    # Chuẩn hoá Unicode và loại bỏ dấu
    nfkd_form = unicodedata.normalize('NFKD', name)
    no_accent = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

    # Tách từ: chỉ lấy chữ và số
    words = re.findall(r'\w+', no_accent)

    # Viết hoa chữ cái đầu mỗi từ (PascalCase)
    #nneu muon luu dang BanTinChieu
    camel_case = ''.join(word.capitalize() for word in words)

    #nneu muon luu dang banTinChieu
    #camel_case = words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    return camel_case
