-- Migration 0002 — cấp quyền cho service_role (backend dùng secret key)
-- Chạy sau 0001_init.sql nếu gặp lỗi "permission denied for table ..."

grant usage on schema public to service_role;

grant select, insert, update, delete on public.document_chunks to service_role;
grant select, insert, update, delete on public.document_relations to service_role;

grant usage, select on all sequences in schema public to service_role;

grant execute on function match_document_chunks(vector, int) to service_role;
