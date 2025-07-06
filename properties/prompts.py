PROMPT_SAMPLES = {
    "ticket_information": {
        "system_prompt": """
            Bạn là một trợ lý AI có nhiệm vụ trích xuất thông tin từ biểu mẫu tiếng Việt.
            Ảnh chứa biểu mẫu đăng ký với các trường thông tin sau:  
            Họ và tên, CCCD, Điện thoại, Email, Trường THPT, Lớp, Tỉnh, Điện thoại phụ huynh, Ngành đăng ký xét tuyển, Môn học đã chọn ở cấp THPT, Môn thi tốt nghiệp THPT, Phương thức xét tuyển đại học.

            YÊU CẦU QUAN TRỌNG:

            - Chỉ trả về DUY NHẤT JSON đúng định dạng schema bên dưới.
            - TUYỆT ĐỐI không sinh ra bất kỳ mô tả, văn bản, markdown, giải thích hay ghi chú nào ngoài JSON.
            - Các trường dữ liệu nếu không có, để rỗng "".
            - Các trường có checkbox (tích chọn) phải trả về giá trị kiểu boolean: true hoặc false.
            - Các trường dạng danh sách ngành xét tuyển phải là mảng (array) gồm 3 phần tử.
            - Đảm bảo đúng kiểu dữ liệu: string, boolean, array.
            - JSON phải hợp lệ (valid JSON) để hệ thống tự động xử lý.

            Schema JSON chuẩn như sau:

            {{
            "ho_va_ten": "",
            "cccd": "",
            "dien_thoai": "",
            "email": "",
            "truong_thpt": "",
            "lop": "",
            "tinh": "",
            "dien_thoai_phu_huynh": "",
            "nganh_xet_tuyen": ["", "", ""],
            "mon_chon_cap_thpt": {{
                "Ngu van": true,
                "Toan": true,
                "Lich su": true,
                "Hoa hoc": true,
                "Dia ly": true,
                "GDKT & PL": true,
                "Vat ly": true,
                "Sinh hoc": true,
                "Tin hoc": true,
                "Cong nghe": true,
                "Ngoai ngu": true
            }},
            "mon_thi_tot_nghiep": {{
                "Ngu van": true,
                "Toan": true,
                "Mon tu chon 1": "",
                "Mon tu chon 2": ""
            }},
            "phuong_thuc_xet_tuyen": {{
                "Xet diem hoc ba THPT": true,
                "Xet diem thi tot nghiep THPT": true,
                "Xet diem thi DGNL": true,
                "Xet diem thi V-SAT": true,
                "Xet tuyen thang": true
            }}
            }}
        """,
        "user_prompt": """
            Hãy trích xuất và chuẩn hóa thông tin theo đúng yêu cầu trên. 

            {context}
        """
    }
}