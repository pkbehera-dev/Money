from dataclasses import dataclass
from typing import Optional

@dataclass
class Transaction:
    id: Optional[int]
    type: str # income, expense, transfer
    amount: float
    category: Optional[str]
    date: str
    account_id: Optional[int]
    to_account_id: Optional[int]
    notes: Optional[str]
    tags: Optional[str]
    recurring_id: Optional[int]
    card_id: Optional[int] = None
    person_id: Optional[int] = None
    deleted_at: Optional[str] = None
    account_name: Optional[str] = None
    to_account_name: Optional[str] = None
    card_name: Optional[str] = None

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            type=row['type'],
            amount=row['amount'],
            category=row['category'],
            date=row['date'],
            account_id=row['account_id'],
            to_account_id=row['to_account_id'],
            notes=row['notes'],
            tags=row['tags'],
            recurring_id=row['recurring_id'],
            card_id=row.get('card_id'),
            person_id=row.get('person_id'),
            deleted_at=row.get('deleted_at')
        )

    def to_ai_format(self):
        """Format the transaction cleanly for AI contextual analysis."""
        return {
            "transaction_id": self.id,
            "type": self.type,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "notes": self.notes,
            "tags": self.tags
        }
