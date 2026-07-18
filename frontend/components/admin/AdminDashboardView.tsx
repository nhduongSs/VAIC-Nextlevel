"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AdminSidebar } from "./AdminSidebar";
import { DocumentTable } from "./DocumentTable";
import { DocumentFormModal } from "./DocumentFormModal";
import { SEED_DOCUMENTS, EMPTY_DOC_FORM, type AdminDocument, type DocumentFormValues } from "@/lib/adminDocuments";

interface AdminDashboardViewProps {
  adminEmail: string;
  onLogout: () => void;
  onGoToChat: () => void;
}

let nextDocId = 100;

export function AdminDashboardView({ adminEmail, onLogout, onGoToChat }: AdminDashboardViewProps) {
  const [documents, setDocuments] = useState<AdminDocument[]>(SEED_DOCUMENTS);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formValues, setFormValues] = useState<DocumentFormValues>(EMPTY_DOC_FORM);

  function openNewDocForm() {
    setEditingId(null);
    setFormValues(EMPTY_DOC_FORM);
    setIsFormOpen(true);
  }

  function openEditDocForm(doc: AdminDocument) {
    setEditingId(doc.id);
    setFormValues({ name: doc.name, category: doc.category, fileName: doc.fileName });
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    setFormValues(EMPTY_DOC_FORM);
  }

  function saveForm() {
    if (!formValues.name.trim()) return;
    const today = new Date().toLocaleDateString("vi-VN");
    if (editingId !== null) {
      setDocuments((prev) => prev.map((d) => (d.id === editingId ? { ...d, ...formValues, updatedAt: today } : d)));
    } else {
      nextDocId += 1;
      setDocuments((prev) => [...prev, { id: nextDocId, ...formValues, updatedAt: today }]);
    }
    closeForm();
  }

  function deleteDoc(id: number) {
    const doc = documents.find((d) => d.id === id);
    if (doc && window.confirm(`Xóa tài liệu "${doc.name}"?`)) {
      setDocuments((prev) => prev.filter((d) => d.id !== id));
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
          <DocumentTable documents={documents} onEdit={openEditDocForm} onDelete={deleteDoc} />
        </div>
      </div>

      {isFormOpen && (
        <DocumentFormModal
          title={editingId !== null ? "Sửa tài liệu" : "Thêm tài liệu mới"}
          values={formValues}
          onChange={setFormValues}
          onSave={saveForm}
          onClose={closeForm}
        />
      )}
    </div>
  );
}
