import io
from openpyxl import Workbook



def generate_expense_report(expenses: list) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Звіт про витрати"
    headers = ["ID", "Опис", "Дата", "Сума (UAH)", "Сума (USD)"]
    sheet.append(headers)
    total_uah = 0
    total_usd = 0

    for expense in expenses:
        sheet.append([
            expense.id,
            expense.description,
            expense.date.strftime('%d.%m.%Y'),
            expense.price_uah,
            expense.price_usd
        ])
        total_uah += expense.price_uah
        total_usd += expense.price_usd

    sheet.append(["", "", "Разом:", total_uah, total_usd])

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()