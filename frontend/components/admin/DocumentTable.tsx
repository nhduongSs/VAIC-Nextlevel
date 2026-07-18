import { FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { AdminDocument } from "@/lib/adminDocuments";

interface DocumentTableProps {
  documents: AdminDocument[];
  onEdit: (doc: AdminDocument) => void;
  onDelete: (id: string) => void;
}

export function DocumentTable({ documents, onEdit, onDelete }: DocumentTableProps) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="grid grid-cols-[2fr_1.1fr_1.2fr_1fr] bg-muted px-[18px] py-2.5 text-xs font-bold text-muted-foreground">
        <span>Tên tài liệu</span>
        <span>Danh mục</span>
        <span>Cập nhật</span>
        <span className="text-right">Thao tác</span>
      </div>
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="grid grid-cols-[2fr_1.1fr_1.2fr_1fr] items-center border-t border-border px-[18px] py-3 text-[13.5px]"
        >
          <span className="flex flex-col gap-0.5 pr-2">
            <span className="font-semibold">{doc.name}</span>
            <span className="flex items-center gap-1 text-[11.5px] text-muted-foreground">
              <FileText className="h-3 w-3" aria-hidden="true" />
              {doc.fileName || "Chưa đính kèm tệp"}
            </span>
          </span>
          <span className="text-muted-foreground">{doc.category}</span>
          <span className="text-[12.5px] text-muted-foreground">{doc.updatedAt}</span>
          <span className="flex justify-end gap-3.5">
            <button
              type="button"
              onClick={() => onEdit(doc)}
              className="cursor-pointer text-[12.5px] font-semibold text-primary hover:underline"
            >
              Sửa
            </button>
            <button
              type="button"
              onClick={() => onDelete(doc.id)}
              className="cursor-pointer text-[12.5px] font-semibold text-destructive hover:underline"
            >
              Xóa
            </button>
          </span>
        </div>
      ))}
    </Card>
  );
}
