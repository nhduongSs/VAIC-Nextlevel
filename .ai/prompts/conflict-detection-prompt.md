# Prompt — Conflict Detection

## Purpose

Dùng để phát hiện mâu thuẫn giữa hai đoạn văn bản pháp lý.

## Prompt Template

```
Phân tích hai đoạn văn bản pháp lý ngân hàng sau và xác định có mâu thuẫn không:

=== Văn bản 1 ===
Nguồn: {doc1_number} ({doc1_date})
Điều khoản: {doc1_section}
Nội dung:
{doc1_content}

=== Văn bản 2 ===
Nguồn: {doc2_number} ({doc2_date})
Điều khoản: {doc2_section}
Nội dung:
{doc2_content}

Nhiệm vụ: Xác định có mâu thuẫn trực tiếp về nội dung không?

Phân tích theo format:
KẾT LUẬN: [CÓ MÂU THUẪN / KHÔNG MÂU THUẪN / KHÔNG XÁC ĐỊNH]
LOẠI MÂU THUẪN: [nếu có: số liệu / quy định / phạm vi / thời hạn / thủ tục]
MÔ TẢ: [giải thích cụ thể điểm mâu thuẫn]
GIẢI QUYẾT ĐỀ XUẤT: [văn bản nào nên ưu tiên và tại sao — dựa vào ngày ban hành và thẩm quyền]
```

## Response Parsing

```python
import re

def parse_conflict_response(response: str) -> ConflictAnalysis:
    conclusion = re.search(r"KẾT LUẬN: (.+)", response).group(1)
    conflict_type = re.search(r"LOẠI MÂU THUẪN: (.+)", response)
    description = re.search(r"MÔ TẢ: (.+)", response, re.DOTALL)

    return ConflictAnalysis(
        has_conflict=conclusion.strip() == "CÓ MÂU THUẪN",
        conflict_type=conflict_type.group(1) if conflict_type else None,
        description=description.group(1).strip() if description else "",
    )
```
