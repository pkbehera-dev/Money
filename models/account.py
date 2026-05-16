from dataclasses import dataclass
from typing import Optional

@dataclass
class Account:
    id: Optional[int]
    name: str
    type: str # Cash, Bank account, Wallet, UPI, Credit cards, Custom
    balance: float
    notes: Optional[str]
    deleted_at: Optional[str] = None

    @classmethod
    def from_row(cls, row):
        # Convert sqlite3.Row or dict-like object to Account
        data = dict(row)
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            type=data.get('type'),
            balance=data.get('balance', 0.0),
            notes=data.get('notes'),
            deleted_at=data.get('deleted_at')
        )
