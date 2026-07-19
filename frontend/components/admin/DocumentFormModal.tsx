"use client";

import type { ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AUTHORITY_LEVEL_OPTIONS,
  DOC_CATEGORIES,
  DOC_TYPE_OPTIONS,
  type DocumentFormValues,
} from "@/lib/adminDocuments";

interface DocumentFormModalProps {
  title: string;
  isEditing: boolean;
  values: DocumentFormValues;
  isSaving: boolean;
  onChange: (values: DocumentFormValues) => void;
  onSave: () => void;
  onClose: () => void;
}

export function DocumentFormModal({
  title,
  isEditing,
  values,
  isSaving,
  onChange,
  onSave,
  onClose,
}: DocumentFormModalProps) {
  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    onChange({
      ...values,
      file,
      name: values.name || file.name.replace(/\.[^/.]+$/, ""),
    });
  }

  const canSave = values.name.trim().length > 0 && (isEditing || values.file !== null) && !isSaving;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="flex max-h-[90vh] w-[560px] max-w-full flex-col gap-3.5 overflow-y-auto rounded-2xl bg-card p-6 shadow-lg"
      >
        <span className="text-[15px] font-bold">{title}</span>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-muted-foreground">Tệp tài liệu</label>
          {isEditing ? (
            <div className="flex items-center gap-2.5 rounded-[9px] border border-dashed border-border bg-muted p-3.5">
              <span className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-[9px] bg-muted-foreground/20 text-muted-foreground">
                <Upload className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="text-[13px] text-muted-foreground">
                {values.existingFileName || "Chưa đính kèm tệp"} (không thể thay tệp, chỉ sửa metadata)
              </span>
            </div>
          ) : (
            <label className="flex cursor-pointer items-center gap-2.5 rounded-[9px] border border-dashed border-border bg-muted p-3.5">
              <input type="file" onChange={handleFileChange} className="hidden" />
              <span className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-[9px] bg-primary text-primary-foreground">
                <Upload className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="text-[13px] text-muted-foreground">
                {values.file?.name || "Chọn tệp (PDF, DOCX...) để tải lên"}
              </span>
            </label>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3.5">
          <div className="col-span-2 flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Tên tài liệu</label>
            <input
              value={values.name}
              onChange={(event) => onChange({ ...values, name: event.target.value })}
              placeholder="VD: Biểu lãi suất tiết kiệm 2026"
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Danh mục (nội bộ)</label>
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

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Loại văn bản</label>
            <select
              value={values.docType}
              onChange={(event) => onChange({ ...values, docType: event.target.value })}
              className="rounded-[9px] border border-border bg-card px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              {DOC_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="col-span-2 flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Cấp thẩm quyền</label>
            <select
              value={values.authorityLevel}
              onChange={(event) => onChange({ ...values, authorityLevel: event.target.value })}
              className="rounded-[9px] border border-border bg-card px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              {AUTHORITY_LEVEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Số hiệu văn bản</label>
            <input
              value={values.docNumber}
              onChange={(event) => onChange({ ...values, docNumber: event.target.value })}
              placeholder="VD: 36/2014/TT-NHNN"
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Cơ quan ban hành</label>
            <input
              value={values.issuingBody}
              onChange={(event) => onChange({ ...values, issuingBody: event.target.value })}
              placeholder="VD: Ngân hàng Nhà nước Việt Nam"
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Ngày ban hành</label>
            <input
              type="date"
              value={values.issuedDate}
              onChange={(event) => onChange({ ...values, issuedDate: event.target.value })}
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Ngày hiệu lực</label>
            <input
              type="date"
              value={values.effectiveDate}
              onChange={(event) => onChange({ ...values, effectiveDate: event.target.value })}
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Ngày hết hiệu lực</label>
            <input
              type="date"
              value={values.expiredDate}
              onChange={(event) => onChange({ ...values, expiredDate: event.target.value })}
              className="rounded-[9px] border border-border px-3 py-2.5 text-[13.5px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>
        </div>

        <div className="flex gap-2.5 pt-1">
          <Button onClick={onSave} disabled={!canSave}>
            {isSaving ? "Đang lưu..." : "Lưu"}
          </Button>
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Hủy
          </Button>
        </div>
      </div>
    </div>
  );
}
