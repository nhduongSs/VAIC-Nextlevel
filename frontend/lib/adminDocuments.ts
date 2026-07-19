import type { DocumentResponse } from "@/lib/api";

export interface AdminDocument {
  id: string;
  name: string;
  category: string;
  updatedAt: string;
  fileName: string;
  docType: string;
  authorityLevel: string;
  docNumber: string;
  issuingBody: string;
  issuedDate: string;
  effectiveDate: string;
  expiredDate: string;
}

export const DOC_CATEGORIES = ["Tiết kiệm có kỳ hạn", "Tiết kiệm online", "Chính sách chung", "Biểu phí"];

// Phải khớp với enum DocumentType phía backend (app/models/enums.py)
export const DOC_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "LAW", label: "Luật" },
  { value: "CIRCULAR", label: "Thông tư" },
  { value: "DECREE", label: "Nghị định" },
  { value: "DECISION", label: "Quyết định" },
  { value: "POLICY", label: "Chính sách nội bộ" },
  { value: "SOP", label: "Quy trình nghiệp vụ" },
  { value: "FAQ", label: "Hỏi đáp thường gặp" },
  { value: "PRODUCT_DOC", label: "Tài liệu sản phẩm" },
  { value: "MANUAL", label: "Sổ tay hướng dẫn" },
  { value: "UNKNOWN", label: "Chưa xác định" },
];

// Phải khớp với enum AuthorityLevel phía backend (app/models/enums.py)
export const AUTHORITY_LEVEL_OPTIONS: { value: string; label: string }[] = [
  { value: "NATIONAL_LAW", label: "Luật Quốc hội ban hành" },
  { value: "NHNN_CIRCULAR", label: "Thông tư Ngân hàng Nhà nước" },
  { value: "NHNN_DECISION", label: "Quyết định Ngân hàng Nhà nước" },
  { value: "INTERNAL_POLICY", label: "Chính sách nội bộ ngân hàng" },
  { value: "DEPARTMENT_SOP", label: "Quy trình cấp phòng ban" },
  { value: "FAQ", label: "Tài liệu hỏi đáp" },
  { value: "UNKNOWN", label: "Chưa xác định" },
];

export interface DocumentFormValues {
  name: string;
  category: string;
  file: File | null;
  existingFileName: string;
  docType: string;
  authorityLevel: string;
  docNumber: string;
  issuingBody: string;
  issuedDate: string;
  effectiveDate: string;
  expiredDate: string;
}

export const EMPTY_DOC_FORM: DocumentFormValues = {
  name: "",
  category: DOC_CATEGORIES[0],
  file: null,
  existingFileName: "",
  docType: "PRODUCT_DOC",
  authorityLevel: "INTERNAL_POLICY",
  docNumber: "",
  issuingBody: "",
  issuedDate: "",
  effectiveDate: "",
  expiredDate: "",
};

export function toAdminDocument(doc: DocumentResponse): AdminDocument {
  return {
    id: doc.id,
    name: doc.title,
    category: doc.tags[0] ?? DOC_CATEGORIES[0],
    updatedAt: new Date(doc.updated_at).toLocaleDateString("vi-VN"),
    fileName: doc.original_filename,
    docType: doc.doc_type,
    authorityLevel: doc.authority_level,
    docNumber: doc.doc_number ?? "",
    issuingBody: doc.issuing_body ?? "",
    issuedDate: doc.issued_date ?? "",
    effectiveDate: doc.effective_date ?? "",
    expiredDate: doc.expired_date ?? "",
  };
}

export function toFormValues(doc: AdminDocument): DocumentFormValues {
  return {
    name: doc.name,
    category: doc.category,
    file: null,
    existingFileName: doc.fileName,
    docType: doc.docType,
    authorityLevel: doc.authorityLevel,
    docNumber: doc.docNumber,
    issuingBody: doc.issuingBody,
    issuedDate: doc.issuedDate,
    effectiveDate: doc.effectiveDate,
    expiredDate: doc.expiredDate,
  };
}
