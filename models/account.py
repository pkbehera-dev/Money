from dataclasses import dataclass
from typing import Optional

@dataclass
class Account:
    id: Optional[int]
    name: str
    type: str # Cash, Bank account, Wallet, UPI, Credit cards, Custom
    balance: float
    notes: Optional[str]

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            name=row['name'],
            type=row['type'],
            balance=row['balance'],
            notes=row['notes']
        )
