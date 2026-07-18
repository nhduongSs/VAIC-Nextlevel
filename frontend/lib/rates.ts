export interface RateTerm {
  months: number;
  ratePercent: number;
}

export const DEPOSIT_TERMS: RateTerm[] = [
  { months: 1, ratePercent: 3.0 },
  { months: 3, ratePercent: 3.7 },
  { months: 6, ratePercent: 4.5 },
  { months: 9, ratePercent: 4.7 },
  { months: 12, ratePercent: 5.0 },
  { months: 18, ratePercent: 5.2 },
  { months: 24, ratePercent: 5.3 },
  { months: 36, ratePercent: 5.5 },
];

export function formatTermLabel(months: number): string {
  if (months >= 12 && months % 12 === 0) return `${months / 12} năm`;
  return `${months} tháng`;
}

export function formatVnd(amount: number): string {
  return `${Math.round(amount).toLocaleString("vi-VN")} đ`;
}

export function calculateInterest(amount: number, months: number) {
  const term = DEPOSIT_TERMS.find((t) => t.months === months) ?? DEPOSIT_TERMS[4];
  const interest = amount * (term.ratePercent / 100) * (term.months / 12);
  return { term, interest, total: amount + interest };
}
