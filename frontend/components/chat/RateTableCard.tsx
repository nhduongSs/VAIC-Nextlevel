import { Card } from "@/components/ui/card";
import { DEPOSIT_TERMS, formatTermLabel } from "@/lib/rates";

export function RateTableCard() {
  return (
    <Card className="overflow-hidden p-0">
      <div className="grid grid-cols-2 bg-muted px-4 py-2.5 text-xs font-bold text-muted-foreground">
        <span>Kỳ hạn</span>
        <span className="text-right">Lãi suất/năm</span>
      </div>
      {DEPOSIT_TERMS.map((term) => (
        <div key={term.months} className="grid grid-cols-2 border-t border-border px-4 py-2 text-sm">
          <span>{formatTermLabel(term.months)}</span>
          <span className="text-right font-bold text-primary">{term.ratePercent.toFixed(1)}%/năm</span>
        </div>
      ))}
      <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
        Số liệu minh họa, tham khảo tại quầy giao dịch để biết lãi suất chính xác.
      </div>
    </Card>
  );
}
