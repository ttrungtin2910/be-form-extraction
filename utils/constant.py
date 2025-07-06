# Ánh xạ tên trường input -> schema chuẩn
FIELD_MAPPING = {
    "Name": "ho_va_ten",
    "CCCD": "cccd",
    "PhoneNumber": "dien_thoai",
    "Email": "email",
    "THPT": "truong_thpt",
    "Class": "lop",
    "Province": "tinh",
    "ParentPhone": "dien_thoai_phu_huynh",
    "PreferredMajor": "nganh_xet_tuyen_1",  # Return to list later
    
    # Môn học đã chọn ở cấp THPT
    "Literature": ("mon_chon_cap_thpt", "Ngu van"),
    "Maths": ("mon_chon_cap_thpt", "Toan"),
    "History": ("mon_chon_cap_thpt", "Lich su"),
    "Chemistry": ("mon_chon_cap_thpt", "Hoa hoc"),
    "Geography": ("mon_chon_cap_thpt", "Dia ly"),
    "GDKT": ("mon_chon_cap_thpt", "GDKT & PL"),
    "Physics": ("mon_chon_cap_thpt", "Vat ly"),
    "Biology": ("mon_chon_cap_thpt", "Sinh hoc"),
    "IT": ("mon_chon_cap_thpt", "Tin hoc"),
    "Technologies": ("mon_chon_cap_thpt", "Cong nghe"),
    "ForeignLanguage": ("mon_chon_cap_thpt", "Ngoai ngu"),

    # Môn thi tốt nghiệp THPT
    "TestLiterature": ("mon_thi_tot_nghiep", "Ngu van"),
    "TestMath": ("mon_thi_tot_nghiep", "Toan"),
    "TestOption1": ("mon_thi_tot_nghiep", "Mon tu chon 1"),
    "TestOption2": ("mon_thi_tot_nghiep", "Mon tu chon 2"),

    # Phương thức xét tuyển
    "UseRecords": ("phuong_thuc_xet_tuyen", "Xet diem hoc ba THPT"),
    "UseTest": ("phuong_thuc_xet_tuyen", "Xet diem thi tot nghiep THPT"),
    "UseDGNL": ("phuong_thuc_xet_tuyen", "Xet diem thi DGNL"),
    "UseVSAT": ("phuong_thuc_xet_tuyen", "Xet diem thi V-SAT"),
    "UseDirectAdmission": ("phuong_thuc_xet_tuyen", "Xet tuyen thang")
}