export interface AdminDocument {
  id: number;
  name: string;
  category: string;
  updatedAt: string;
  fileName: string;
}

export const DOC_CATEGORIES = ["Tiết kiệm có kỳ hạn", "Tiết kiệm online", "Chính sách chung", "Biểu phí"];

export const SEED_DOCUMENTS: AdminDocument[] = [
  {
    id: 1,
    name: "Biểu lãi suất tiết kiệm 2026",
    category: "Tiết kiệm có kỳ hạn",
    updatedAt: "17/07/2026",
    fileName: "bieu-lai-suat-2026.pdf",
  },
  {
    id: 2,
    name: "Điều kiện tất toán trước hạn",
    category: "Chính sách chung",
    updatedAt: "15/07/2026",
    fileName: "dieu-kien-tat-toan.pdf",
  },
  {
    id: 3,
    name: "Ưu đãi gửi tiết kiệm online",
    category: "Tiết kiệm online",
    updatedAt: "10/07/2026",
    fileName: "uu-dai-online.docx",
  },
];

export interface DocumentFormValues {
  name: string;
  category: string;
  fileName: string;
}

export const EMPTY_DOC_FORM: DocumentFormValues = { name: "", category: DOC_CATEGORIES[0], fileName: "" };
