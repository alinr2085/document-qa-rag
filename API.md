# مستندات API

Base URL: `http://localhost:8000/api/` — مستندات تعاملی: `/api/docs/` (Swagger)، اسکیما: `/api/schema/`.
اگر `API_REQUIRE_AUTH=true` باشد از Basic Auth استفاده کنید: `curl -u admin:admin12345 ...`

| Method | Path | توضیح |
|---|---|---|
| GET | `/documents/` | لیست اسناد (صفحه‌بندی ۲۰تایی؛ `?page=2`) |
| POST | `/documents/` | ایجاد سند (JSON با `content` یا multipart با `file` docx) |
| GET | `/documents/{id}/` | جزئیات سند و متن کامل |
| PUT | `/documents/{id}/` | ویرایش کامل |
| PATCH | `/documents/{id}/` | ویرایش جزئی |
| DELETE | `/documents/{id}/` | حذف سند و بخش‌هایش |
| POST | `/search/` | یافتن بخش‌های مرتبط با پرسش |
| POST | `/ask/` | پرسش و دریافت پاسخ (در تاریخچه ذخیره می‌شود) |
| GET | `/history/` | تاریخچه پرسش و پاسخ (صفحه‌بندی) |
| GET | `/history/{id}/` | یک مورد تاریخچه |
| DELETE | `/history/{id}/` | حذف از تاریخچه |

> شناسه‌ها (id) یکتا و صعودی‌اند ولی پیوسته نیستند (sequence دیتابیس Oracle). شناسه را از خروجی لیست بردارید.

## نمونه‌ها

ایجاد سند با متن:
```bash
curl -X POST localhost:8000/api/documents/ -H 'Content-Type: application/json' \
  -d '{"title":"نمونه","content":"متن سند ..."}'
```

آپلود docx:
```bash
curl -X POST localhost:8000/api/documents/ -F title="سیاست مرخصی" -F file=@sample_data/leave_policy.docx
```

ویرایش:
```bash
curl -X PATCH localhost:8000/api/documents/1/ -H 'Content-Type: application/json' -d '{"title":"عنوان جدید"}'
```

حذف:
```bash
curl -X DELETE localhost:8000/api/documents/1/
```
پاسخ موفق: `204 No Content`

جست‌وجو:
```bash
curl -X POST localhost:8000/api/search/ -H 'Content-Type: application/json' \
  -d '{"query":"کمک‌هزینه اینترنت دورکاری","top_k":3}'
```
پاسخ: `[{"document_id":2,"title":"...","chunk_index":0,"score":0.032,"text":"..."}]`

پرسش (`top_k` اختیاری است):
```bash
curl -X POST localhost:8000/api/ask/ -H 'Content-Type: application/json' \
  -d '{"question":"مرخصی استحقاقی در سال چند روز است؟"}'
```
پاسخ (201):
```json
{
  "id": 1,
  "question": "مرخصی استحقاقی در سال چند روز است؟",
  "answer": "هر کارمند رسمی ۲۶ روز مرخصی استحقاقی دارد [1].",
  "sources": [{"document_id": 1, "title": "سیاست مرخصی شرکت", "chunk_index": 0, "score": 0.033, "snippet": "..."}],
  "model_name": "gemini-3.1-flash-lite",
  "response_time_ms": 2310,
  "created_at": "2026-11-21T18:00:00+03:30"
}
```

مشاهده و حذف تاریخچه:
```bash
curl localhost:8000/api/history/
curl localhost:8000/api/history/1/
curl -X DELETE localhost:8000/api/history/1/
```

## کدهای خطا

- `400` ورودی نامعتبر (مثلاً سند بدون `file` و `content`)
- `404` یافت نشد
- `502` خطا در ارتباط با مدل زبانی (مثلاً سقف سهمیه‌ی رایگان `429` یا شلوغی موقت سرویس)
- `503` کلید `OPENROUTER_API_KEY` تنظیم نشده است

## سوال‌های نمونه برای تست

- مرخصی استحقاقی در سال چند روز است؟
- چند روز در هفته می‌توان دورکاری کرد؟
- رمز عبور حداقل چند کاراکتر باید باشد؟
- ایمیل فیشینگ را به کجا گزارش کنم؟