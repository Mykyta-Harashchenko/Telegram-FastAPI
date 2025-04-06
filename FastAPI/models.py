from sqlalchemy import Integer, String, Date, Boolean, Text, ForeignKey, DateTime, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column

Base = declarative_base()

class Expenses(Base):
    __tablename__ = 'expenses'
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    price_uah = mapped_column(Integer, primary_key=True)
    price_usd = mapped_column(Integer, primary_key=True)
    date = mapped_column(Date, primary_key=True)
    description = mapped_column(String(255))

