import type { DocumentResponse } from "@/lib/api";

export interface AdminDocument {
  id: string;
  name: string;
  category: string;
  updatedAt: string;
  fileName: string;
}

export const DOC_CATEGORIES = ["Tiết kiệm có kỳ hạn", "Tiết kiệm online", "Chính sách chung", "Biểu phí"];

export interface DocumentFormValues {
  name: string;
  category: string;
  file: File | null;
  existingFileName: string;
}

export const EMPTY_DOC_FORM: DocumentFormValues = {
  name: "",
  category: DOC_CATEGORIES[0],
  file: null,
  existingFileName: "",
};

export function toAdminDocument(doc: DocumentResponse): AdminDocument {
  return {
    id: doc.id,
    name: doc.title,
    category: doc.tags[0] ?? DOC_CATEGORIES[0],
    updatedAt: new Date(doc.updated_at).toLocaleDateString("vi-VN"),
    fileName: doc.original_filename,
  };
}
