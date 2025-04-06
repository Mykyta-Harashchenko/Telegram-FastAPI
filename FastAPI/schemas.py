from pydantic import BaseModel, EmailStr
from datetime import date


class ExpenseCreate(BaseModel):
    price_uah: int
    date_created: date
    description: str

class ExpenseUpdate(BaseModel):
    description: str
    price_uah: float


class ExpenseResponse(BaseModel):
    id: int
    description: str
    date: date
    price_uah: float
    price_usd: float

    class Config:
        orm_mode = True