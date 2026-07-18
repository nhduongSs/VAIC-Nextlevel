# Chat Dashboard UI — Design Spec

Ngày: 2026-07-18
Trạng thái: Approved (chờ implementation plan)

## Bối cảnh

Dự án RAG Knowledge Base — Tiền gửi (SHB Bank), hackathon 48h. Backend FastAPI đã có endpoint `POST /api/v1/chat` theo `doc/API_CONTRACT.md`. Thư mục `frontend/` hiện chỉ có các folder rỗng (`app/`, `components/`, `lib/`), chưa scaffold.

`doc/TechStack_RAG_TienGui_SHB.md` ban đầu khuyến nghị scope UI tối giản (1 màn hình chat + khu hiển thị trích dẫn/cảnh báo) để tiết kiệm thời gian dựng Next.js trong 48h. Yêu cầu lần này là dựng dashboard đầy đủ hơn, lấy cảm hứng bố cục/thẩm mỹ từ template Dribbble "Synapse AI Chat Dashboard" — chấp nhận tốn thêm thời gian dựng so với phương án tối giản ban đầu.

## Mục tiêu

Dựng 1 dashboard chat 3 cột (sidebar phiên chat / khung chat / panel trích dẫn-conflict), style dark mode cảm hứng Synapse, kết nối thật vào backend đã có, quản lý phiên chat qua localStorage (backend không có API list/lưu lịch sử phiên).

## Kiến trúc & Stack

- **Framework**: Next.js 14 (App Router) + TypeScript, scaffold mới trong `frontend/`.
- **Styling**: Tailwind CSS + shadcn/ui (Button, Card, Tabs, ScrollArea, Badge, Avatar).
- **Route**: 1 route duy nhất `/` chứa toàn bộ dashboard.
- **Theme**: dark mode mặc định, accent tím/xanh gradient (Synapse-style), font Inter, glass-card nhẹ (backdrop-blur + border mờ). Không làm light/dark toggle.
- **Ngôn ngữ UI**: tiếng Việt (đối tượng người dùng SHB Bank).
- **API layer**: `lib/api.ts` — wrapper fetch, base URL từ `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), hàm `sendChatMessage(sessionId, message)` gọi `POST /api/v1/chat`, timeout 30s.
- **Session layer**: `lib/sessions.ts` — quản lý phiên chat hoàn toàn ở localStorage, schema:
  ```ts
  type StoredSession = {
    id: string;          // crypto.randomUUID()
    title: string;       // lấy từ tin nhắn user đầu tiên
    createdAt: string;
    messages: Message[]; // gồm cả sources/conflicts đã gắn kèm
  };
  ```

## Cấu trúc thư mục

```
frontend/
  app/
    page.tsx                 # dashboard chính, ghép 3 cột
    layout.tsx                # font, theme provider
  components/
    sidebar/
      Sidebar.tsx              # cột trái, container
      SessionList.tsx          # danh sách phiên, click chuyển session
      NewChatButton.tsx
    chat/
      ChatWindow.tsx           # cột giữa, container
      MessageList.tsx          # scroll list, auto-scroll bottom
      MessageBubble.tsx        # variant: user / assistant / blocked / error
      TypingIndicator.tsx      # loading state khi chờ backend
      MessageInput.tsx         # textarea + send button
    insights/
      InsightsPanel.tsx        # cột phải, container, tabs
      SourcesTab.tsx           # list sources[] của message đang chọn
      ConflictsTab.tsx         # list conflicts[] (badge cảnh báo nếu có)
    ui/                        # shadcn primitives
  lib/
    api.ts
    sessions.ts
    blockReasons.ts            # map block_reason -> câu tiếng Việt dễ hiểu
  types/
    chat.ts                    # Message, Source, Conflict, ChatResponse
```

## Hành vi các thành phần

- **MessageBubble**: click vào bubble `assistant` (không blocked) → set "selected message" → `InsightsPanel` cập nhật theo `sources`/`conflicts` của message đó. Mặc định chọn message `assistant` mới nhất khi có phản hồi mới.
- **InsightsPanel**: 2 tab.
  - "Nguồn trích dẫn": liệt kê `doc_id`, `title`, `clause`, `effective_date`.
  - "Mâu thuẫn": badge đỏ nếu `conflicts.length > 0`, hiển thị `description` + `conflicting_sources`.
  - Không có dữ liệu → empty state, không lỗi.
- **Sidebar**: mỗi session item hiện `title` + timestamp. "New Chat" tạo `session_id` mới nhưng chưa ghi localStorage cho tới khi có tin nhắn đầu tiên (tránh session rỗng tồn tại).
- **Responsive**: ưu tiên desktop/laptop (bối cảnh demo hackathon). Không đầu tư kỹ cho mobile; panel phải có thể collapse ở màn hẹp nhưng không bắt buộc hoàn thiện.

## Data flow — gửi 1 tin nhắn

1. User gõ, nhấn gửi → optimistic append `MessageBubble` (role: `user`) vào `MessageList`, lưu localStorage ngay.
2. Hiện `TypingIndicator`, disable input.
3. `sendChatMessage(sessionId, message)` → `POST /api/v1/chat`.
4. Xử lý response:
   - `blocked: true` → append bubble variant `blocked`, nội dung lấy từ `blockReasons.ts` (map `block_reason` sang câu tiếng Việt). Nếu backend không trả `answer` khi blocked, fallback hiển thị text từ `block_reason`.
   - `blocked: false` → append bubble `assistant` với `answer`, gắn kèm `sources`/`conflicts` vào message object, tự động set làm "selected message" → `InsightsPanel` refresh theo message này.
5. Lưu message mới (kèm sources/conflicts) vào session trong localStorage — reload trang vẫn xem lại được, không mất dữ liệu.
6. Ẩn typing indicator, enable lại input.

## Error handling

- Network fail / timeout / lỗi 5xx → bubble variant `error` màu đỏ nhạt, text "Không kết nối được máy chủ", kèm nút **Thử lại** (resend cùng nội dung, không tạo thêm bubble user trùng).
- Fetch timeout: 30s.
- Session chưa có tin nhắn nào → không gọi API, không phát sinh lỗi.

## block_reason mapping (blockReasons.ts)

| block_reason | Hiển thị |
|---|---|
| `out_of_scope` | Câu hỏi ngoài phạm vi sản phẩm tiền gửi SHB |
| `pii_detected` | Phát hiện thông tin cá nhân nhạy cảm trong câu hỏi |
| `unsafe_advice_request` | Không thể tư vấn tài chính cá nhân cụ thể |
| `prompt_injection` | Yêu cầu không hợp lệ |
| `input_too_long` | Câu hỏi quá dài |
| `low_confidence_answer` | Không đủ dữ liệu để trả lời chính xác |

## Testing

Không viết automated test cho FE (đúng scope thời gian hackathon 48h). Verify thủ công qua chạy `npm run dev`, thử 3 case thật với backend đang chạy:
1. Câu hỏi trả lời bình thường, có `sources`.
2. Câu hỏi có `conflicts` (nếu data test có case xung đột).
3. Câu hỏi bị `blocked` (PII hoặc ngoài phạm vi).

## Ngoài phạm vi (out of scope)

- Không có trang phụ ngoài `/`.
- Không có light/dark toggle.
- Không có API backend mới (list session, lưu lịch sử server-side).
- Không tối ưu mobile.
- Không có automated test suite cho FE.
