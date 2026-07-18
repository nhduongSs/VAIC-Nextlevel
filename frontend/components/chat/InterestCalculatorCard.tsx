"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { DEPOSIT_TERMS, calculateInterest, formatTermLabel, formatVnd } from "@/lib/rates";

export function InterestCalculatorCard() {
  const [amount, setAmount] = useState(100_000_000);
  const [months, setMonths] = useState(12);
  const { term, interest, total } = calculateInterest(amount, months);

  return (
    <Card className="flex flex-col gap-3 p-4">
      <span className="text-sm font-bold">Công cụ tính lãi suất nhanh</span>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-muted-foreground">Số tiền gửi (VNĐ)</label>
        <input
          type="number"
          value={amount}
          onChange={(event) => setAmount(Number(event.target.value) || 0)}
          className="rounded-md border border-border px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-muted-foreground">Kỳ hạn</label>
        <select
          value={months}
          onChange={(event) => setMonths(Number(event.target.value))}
          className="rounded-md border border-border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        >
          {DEPOSIT_TERMS.map((t) => (
            <option key={t.months} value={t.months}>
              {formatTermLabel(t.months)} — {t.ratePercent.toFixed(1)}%/năm
            </option>
          ))}
        </select>
      </div>

      <div className="mt-1 flex flex-col gap-2 rounded-lg bg-muted p-3.5">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Lãi suất áp dụng</span>
          <span className="font-bold">{term.ratePercent.toFixed(1)}%/năm</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Tiền lãi dự kiến</span>
          <span className="font-bold">{formatVnd(interest)}</span>
        </div>
        <div className="flex justify-between border-t border-border pt-2 text-sm">
          <span className="font-bold">Tổng nhận cuối kỳ</span>
          <span className="font-extrabold text-primary">{formatVnd(total)}</span>
        </div>
      </div>
    </Card>
  );
}
