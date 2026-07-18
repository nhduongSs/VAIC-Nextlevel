"""PgBankProductRepository — Lớp C (bank_products), tra cứu lãi suất SQL chính xác."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import BankProductModel


class PgBankProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, rows: list[BankProductModel]) -> None:
        self._session.add_all(rows)
        await self._session.flush()

    async def delete_by_bank(self, bank: str) -> None:
        await self._session.execute(
            delete(BankProductModel).where(BankProductModel.bank == bank)
        )

    async def compare(
        self,
        term: str | None = None,
        customer_segment: str = "ca_nhan",
        bank: str | None = None,
        product_category: str = "lai_suat_tien_gui",
    ) -> list[BankProductModel]:
        conditions = [
            BankProductModel.product_category == product_category,
            BankProductModel.customer_segment == customer_segment,
        ]
        if term:
            conditions.append(BankProductModel.term.ilike(f"%{term}%"))
        if bank:
            conditions.append(BankProductModel.bank == bank)

        stmt = (
            select(BankProductModel)
            .where(*conditions)
            .order_by(BankProductModel.bank, BankProductModel.term_months)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
