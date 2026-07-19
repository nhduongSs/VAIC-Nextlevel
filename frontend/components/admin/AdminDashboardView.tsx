"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AdminSidebar } from "./AdminSidebar";
import { DocumentTable } from "./DocumentTable";
import { DocumentFormModal } from "./DocumentFormModal";
import {
  EMPTY_DOC_FORM,
  toAdminDocument,
  toFormValues,
  type AdminDocument,
  type DocumentFormValues,
} from "@/lib/adminDocuments";
import { ApiError, createDocument, deleteDocument, listDocuments, updateDocument } from "@/lib/api";

interface AdminDashboardViewProps {
  adminEmail: string;
  permissions: string[];
  onLogout: () => void;
  onGoToChat: () => void;
}

export function AdminDashboardView({ adminEmail, permissions, onLogout, onGoToChat }: AdminDashboardViewProps) {
  const canEdit = permissions.includes("documents:manage");
  const canDelete = permissions.includes("documents:delete");
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<DocumentFormValues>(EMPTY_DOC_FORM);

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function loadDocuments() {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await listDocuments();
      setDocuments(docs.map(toAdminDocument));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không tải được danh sách tài liệu");
    } finally {
      setIsLoading(false);
    }
  }

  function openNewDocForm() {
    setEditingId(null);
    setFormValues(EMPTY_DOC_FORM);
    setIsFormOpen(true);
  }

  function openEditDocForm(doc: AdminDocument) {
    setEditingId(doc.id);
    setFormValues(toFormValues(doc));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    setFormValues(EMPTY_DOC_FORM);
  }

  async function saveForm() {
    if (!formValues.name.trim()) return;
    if (editingId === null && !formValues.file) return;

    setIsSaving(true);
    setError(null);
    try {
      if (editingId !== null) {
        await updateDocument(editingId, formValues);
      } else {
        await createDocument(formValues.file as File, formValues);
      }
      await loadDocuments();
      closeForm();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lưu tài liệu thất bại");
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteDoc(id: string) {
    const doc = documents.find((d) => d.id === id);
    if (!doc || !window.confirm(`Xóa tài liệu "${doc.name}"?`)) return;

    setError(null);
    try {
      await deleteDocument(id);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Xóa tài liệu thất bại");
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <AdminSidebar adminEmail={adminEmail} onLogout={onLogout} onGoToChat={onGoToChat} />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-border bg-card px-[30px] py-5">
          <div className="flex flex-col">
            <span className="text-[17px] font-extrabold">Tài liệu điều khoản gửi tiền</span>
            <span className="text-[12.5px] text-muted-foreground">
              Quản lý nội dung nguồn cho trợ lý AI tham chiếu khi trả lời
            </span>
          </div>
          <Button onClick={openNewDocForm}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Thêm tài liệu
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-[30px]">
          {error && (
            <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2.5 text-[13px] text-destructive">
              {error}
            </div>
          )}
          {isLoading ? (
            <div className="text-[13.5px] text-muted-foreground">Đang tải danh sách tài liệu...</div>
          ) : (
            <DocumentTable
              documents={documents}
              canEdit={canEdit}
              canDelete={canDelete}
              onEdit={openEditDocForm}
              onDelete={deleteDoc}
            />
          )}
        </div>
      </div>

      {isFormOpen && (
        <DocumentFormModal
          title={editingId !== null ? "Sửa tài liệu" : "Thêm tài liệu mới"}
          isEditing={editingId !== null}
          values={formValues}
          isSaving={isSaving}
          onChange={setFormValues}
          onSave={saveForm}
          onClose={closeForm}
        />
      )}
    </div>
  );
}
