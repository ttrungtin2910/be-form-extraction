
from google.cloud.documentai_v1.types.document import Document
from utils.constant import FIELD_MAPPING

def post_process(document: Document):
    document_information = {}

    for entity in document.entities:
        data_type = entity_dtype(entity)

        if data_type == 'boolean':
            content = entity.normalized_value.boolean_value
        else:
            content = entity.text_anchor.content
        
        document_information[entity.type_] = content
    
    # Convert to common format
    convert_to_common_format = transform(document_information)
    return convert_to_common_format

def entity_dtype(entity) -> str:
    """
        Return the data‑type of a `Document.Entity` as a string
        ('date', 'money', 'float', …). Falls back to 'text'.
    """
    if entity.text_anchor.content != '':
        return "text"                        # no normalization → it’s plain text
    else:
        return "boolean"


def transform(input_data: dict) -> dict:
    # Schema kết quả đầu ra chuẩn
    output = {
        "ho_va_ten": "",
        "cccd": "",
        "dien_thoai": "",
        "email": "",
        "truong_thpt": "",
        "lop": "",
        "tinh": "",
        "dien_thoai_phu_huynh": "",
        "nganh_xet_tuyen": ["", "", ""],
        "mon_chon_cap_thpt": {
            "Ngu van": False, "Toan": False, "Lich su": False, "Hoa hoc": False,
            "Dia ly": False, "GDKT & PL": False, "Vat ly": False, "Sinh hoc": False,
            "Tin hoc": False, "Cong nghe": False, "Ngoai ngu": False
        },
        "mon_thi_tot_nghiep": {
            "Ngu van": False, "Toan": False, "Mon tu chon 1": "", "Mon tu chon 2": ""
        },
        "phuong_thuc_xet_tuyen": {
            "Xet diem hoc ba THPT": False,
            "Xet diem thi tot nghiep THPT": False,
            "Xet diem thi DGNL": False,
            "Xet diem thi V-SAT": False,
            "Xet tuyen thang": False
        }
    }

    for key, value in input_data.items():
        if key not in FIELD_MAPPING:
            continue

        mapped = FIELD_MAPPING[key]

        if isinstance(mapped, str):
            if mapped == "nganh_xet_tuyen_1":
                output["nganh_xet_tuyen"][0] = value
            else:
                output[mapped] = value

        elif isinstance(mapped, tuple) and len(mapped) == 2:
            group, subfield = mapped
            if group in output and isinstance(output[group], dict):
                output[group][subfield] = value

    return output