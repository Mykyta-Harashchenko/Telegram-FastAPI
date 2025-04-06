import io

import openpyxl
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi.responses import StreamingResponse

from starlette import status

from FastAPI.db import get_db
from FastAPI import models, schemas
from FastAPI.currency_parser import get_usd_exchange_rate
from reports.report_generator import generate_expense_report

app = FastAPI(
    title="Expenses Tracker API"
)


@app.post("/expenses/", response_model=schemas.ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def add_expense(expense: schemas.ExpenseCreate, db: AsyncSession = Depends(get_db)):
    usd_rate = get_usd_exchange_rate()
    if usd_rate == 0.0:
        raise HTTPException(status_code=500, detail="Не вдалося отримати курс USD")

    amount_usd = round(expense.price_uah / usd_rate, 2)

    new_expense = models.Expenses(

        description=expense.description,
        date=expense.date_created,
        price_uah=expense.price_uah,
        price_usd=amount_usd
    )
    db.add(new_expense)
    await db.commit()
    await db.refresh(new_expense)
    return new_expense


@app.get("/expenses/", response_model=list[schemas.ExpenseResponse])
async def get_expenses(start_date: str, end_date: str, db: AsyncSession = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%d.%m.%Y").date()
        end = datetime.strptime(end_date, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат дати. Використовуйте dd.mm.YYYY")

    query = select(models.Expenses).where(models.Expenses.date.between(start, end))
    result = await db.execute(query)
    return result.scalars().all()


@app.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    query = select(models.Expenses).where(models.Expenses.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="Витрату не знайдено")

    await db.delete(expense)
    await db.commit()
    return {"message": "Витрату успішно видалено"}


@app.get('/expenses/{expense_id}', response_model=schemas.ExpenseResponse)
async def get_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    query = select(models.Expenses).where(models.Expenses.id == expense_id)
    result = await db.execute(query)
    return result.scalar_one()

@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseResponse)
async def update_expense(expense_id: int, updated: schemas.ExpenseUpdate, db: AsyncSession = Depends(get_db)):
    query = select(models.Expenses).where(models.Expenses.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="Витрату не знайдено")

    usd_rate = get_usd_exchange_rate()
    if usd_rate == 0.0:
        raise HTTPException(status_code=500, detail="Не вдалося отримати курс USD")

    expense.description = updated.description
    expense.price_uah = updated.price_uah
    expense.price_usd = round(updated.price_uah / usd_rate, 2)

    await db.commit()
    await db.refresh(expense)
    return expense


@app.get("/expenses/report/")
async def get_expense_report(start_date: str, end_date: str, db: AsyncSession = Depends(get_db)):
    try:
        start = datetime.strptime(start_date, "%d.%m.%Y").date()
        end = datetime.strptime(end_date, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат дати. Використовуйте dd.mm.YYYY")

    query = select(models.Expenses).where(models.Expenses.date.between(start, end))
    result = await db.execute(query)
    expenses = result.scalars().all()

    if not expenses:
        raise HTTPException(status_code=404, detail="Витрат за вказаний період не знайдено")

    report_bytes = generate_expense_report(expenses)

    return StreamingResponse(io.BytesIO(report_bytes),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=expense_report.xlsx"})

@app.get("/expenses/all/")
async def get_all_expenses_xlsx(db: AsyncSession = Depends(get_db)):
    query = select(models.Expenses).order_by(models.Expenses.date)
    result = await db.execute(query)
    expenses = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Всі витрати"

    ws.append(["ID", "Опис", "Дата", "UAH", "USD"])

    for exp in expenses:
        ws.append([exp.id, exp.description, exp.date.strftime('%d.%m.%Y'), exp.price_uah, exp.price_usd])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=all_expenses.xlsx"})


