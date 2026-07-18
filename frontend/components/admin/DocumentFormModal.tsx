"use client";

import type { ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DOC_CATEGORIES, type DocumentFormValues } from "@/lib/adminDocuments";

interface DocumentFormModalProps {
  title: string;
  values: DocumentFormValues;
  onChange: (values: DocumentFormValues) => void;
  onSave: () => void;
  onClose: () => void;
}

export function DocumentFormModal({ title, values, onChange, onSave, onClose }: DocumentFormModalProps) {
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    onChange({
      ...values,
      fileName: file.name,
      name: values.name || file.name.replace(/\.[^/.]+$/, ""),
    });
  }

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="flex w-[480px] max-w-full flex-col gap-3.5 rounded-2xl bg-card p-6 shadow-lg"
      >
        <span className="text-[15px] font-bold">{title}</span>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-muted-foreground">Tệp tài liệu</label>
          <label className="flex cursor-pointer items-center gap-2.5 rounded-[9px] border border-dashed border-border bg-muted p-3.5">
            <input type="file" onChange={handleFileChange} className="hidden" />
            <span className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-[9px] bg-primary text-primary-foreground">
              <Upload className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-[13px] text-muted-foreground">
              {values.fileName || "Chọn tệp (PDF, DOCX...) để tải lên"}
            </span>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3.5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Tên tài liệu</label>
            <input
              value={values.name}
              onChange={(event) => onChange({ ...values, name: event.target.value })}
              placeholder="VD: Biểu lãi suất tiết kiệm 2026"
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Danh mục</label>
            <select
              value={values.category}
              onChange={(event) => onChange({ ...values, category: event.target.value })}
              className="rounded-[9px] border border-border bg-card px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              {DOC_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-2.5 pt-1">
          <Button onClick={onSave}>Lưu</Button>
          <Button variant="outline" onClick={onClose}>
            Hủy
          </Button>
        </div>
      </div>
    </div>
  );
}
