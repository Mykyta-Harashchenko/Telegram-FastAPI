import asyncio
import io
import logging
import os
import re
import sys
from datetime import datetime
import json

from aiogram import Bot, Dispatcher, html, F, types
from aiogram.client.default import DefaultBotProperties
import aiohttp
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, InputFile, FSInputFile

from keyboards import (add_expense, remove_expense, get_review, patch_expense)
from FastAPI.config import config
from states import AddExpenseState, ReportState, DeleteExpenseState, UpdateExpenseState
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

TOKEN = config.BOT_TOKEN
API_URL = config.API_URL

dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def get_combined_kb() -> ReplyKeyboardMarkup:
    add = await add_expense()
    delete = await remove_expense()
    review = await get_review()
    patch = await patch_expense()

    kb = ReplyKeyboardMarkup(
        keyboard=[[add, delete, review, patch]],
        resize_keyboard=True
    )
    return kb


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!", reply_markup=await get_combined_kb())


@dp.message(F.text == "Додати статтю витрат")
async def start_add_expense(message: Message, state: FSMContext):
    await message.answer("Введіть назву статті витрат:")
    await state.set_state(AddExpenseState.name)


@dp.message(AddExpenseState.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть дату у форматі dd.mm.YYYY:")
    await state.set_state(AddExpenseState.date)


@dp.message(AddExpenseState.date)
async def process_date(message: Message, state: FSMContext):
    date_text = message.text
    if not re.match(r"\d{2}\.\d{2}\.\d{4}", date_text):
        await message.answer("Невірний формат дати. Спробуйте ще раз (dd.mm.YYYY):")
        return
    await state.update_data(date=date_text)
    await message.answer("Введіть суму витрат (ціле число або дробове):")
    await state.set_state(AddExpenseState.price)


@dp.message(AddExpenseState.price)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(float(message.text.replace(',', '.')))
    except ValueError:
        await message.answer("Невірний формат суми. Спробуйте ще раз:")
        return
    await state.update_data(amount=amount)
    data = await state.get_data()
    try:
        date_object = datetime.strptime(data["date"], "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Невірний формат дати.")
        return

    payload = {
        "description": data["name"],
        "date_created": date_object.isoformat(),
        "price_uah": data["amount"]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{API_URL}/expenses/", json=payload) as resp:
                if resp.status == 201:
                    await message.answer("Витрату успішно додано!", reply_markup=await get_combined_kb())
                else:
                    text = await resp.text()
                    await message.answer(f"Помилка: {resp.status}\n{text}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

    await state.clear()

# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


@dp.message(F.text == "Отримати звіт")
async def get_report_start(message: Message, state: FSMContext):
    await message.answer("Введіть дату початку періоду (dd.mm.YYYY):")
    await state.set_state(ReportState.start)


@dp.message(ReportState.start)
async def get_report_end(message: Message, state: FSMContext):
    if not re.match(r"\d{2}\.\d{2}\.\d{4}", message.text):
        await message.answer("Невірний формат дати. Спробуйте ще раз.")
        return
    await state.update_data(start_date=message.text)
    await message.answer("Введіть дату кінця періоду (dd.mm.YYYY):")
    await state.set_state(ReportState.end)


@dp.message(ReportState.end)
async def process_end_date(message: Message, state: FSMContext):
    end_date = message.text
    if not re.match(r"\d{2}\.\d{2}\.\d{4}", end_date):
        await message.answer("Невірний формат дати. Спробуйте ще раз (dd.mm.YYYY):")
        return

    data = await state.get_data()
    start_date = data["start_date"]

    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/expenses/report/", params=params) as response:
                if response.status == 200:
                    content = await response.read()

                    file_path = "report.xlsx"
                    with open(file_path, "wb") as f:
                        f.write(content)

                    file = FSInputFile(file_path)

                    await message.answer_document(
                        document=file,
                        caption=f"Ваш звіт витрат з {start_date} по {end_date}"
                    )

                    total_uah = response.headers.get("X-Total-UAH")
                    if total_uah:
                        await message.answer(f"Загальна сума витрат: {total_uah} грн")

                    os.remove(file_path)
                else:
                    await message.answer(f"Помилка при отриманні звіту: {response.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

    await state.clear()
    await message.answer("Ви повернулись до головного меню", reply_markup=await get_combined_kb())

# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

@dp.message(F.text == "Видалити статтю витрат")
async def start_delete_expense(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/expenses/all/") as response:
                if response.status == 200:
                    content = await response.read()

                    file_path = "report.xlsx"
                    with open(file_path, "wb") as f:
                        f.write(content)

                    file = FSInputFile(file_path)

                    await message.answer_document(
                        document=file,
                        caption=f"Ваш звіт витрат за весь час.\nВведіть ID статті, яку хочете видалити:"
                        )
                    await state.set_state(DeleteExpenseState.waiting_for_id)
                else:
                    await message.answer(f"Не вдалося отримати список витрат: {response.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

@dp.message(DeleteExpenseState.waiting_for_id)
async def process_delete_id(message: Message, state: FSMContext):
    try:
        expense_id = int(message.text)
    except ValueError:
        await message.answer("Введіть коректний числовий ID:")
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.delete(f"{API_URL}/expenses/{expense_id}") as resp:
                if resp.status == 200:
                    await message.answer("Витрату успішно видалено!")
                elif resp.status == 404:
                    await message.answer("Витрату з таким ID не знайдено.")
                else:
                    await message.answer(f"Помилка при видаленні: {resp.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

    await state.clear()
    await message.answer("Ви повернулись до головного меню", reply_markup=await get_combined_kb())

#////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
@dp.message(F.text == "Відредагувати статтю витрат")
async def start_patch_expense(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/expenses/all/") as response:
                if response.status == 200:
                    content = await response.read()

                    file_path = "report.xlsx"
                    with open(file_path, "wb") as f:
                        f.write(content)

                    file = FSInputFile(file_path)

                    await message.answer_document(
                        document=file,
                        caption=f"Ваш звіт витрат за весь час.\nВведіть ID статті, яку хочете відредагувати:"
                        )
                    await state.set_state(UpdateExpenseState.waiting_for_id)
                else:
                    await message.answer(f"Не вдалося отримати список витрат: {response.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

@dp.message(UpdateExpenseState.waiting_for_id)
async def process_delete_id(message: Message, state: FSMContext):
    try:
        expense_id = int(message.text)
    except ValueError:
        await message.answer("Введіть коректний числовий ID:")
        return
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/expenses/{expense_id}") as response:
                if response.status == 200:
                    expense_data = await response.json()
                    description = expense_data["description"]
                    price_uah = expense_data["price_uah"]
                    await message.answer(
                        f"Ось поточні дані витрати:\n"
                        f"ID: {expense_id}\n"
                        f"Опис: {description}\n"
                        f"Сума: {price_uah} грн\n\n"
                        f"Введіть новий опис витрати:"
                    )

                    await state.update_data(expense_id=expense_id)
                    await state.set_state(UpdateExpenseState.waiting_for_description)
                else:
                    await message.answer(f"Статтю витрат не знайдено: {response.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

@dp.message(UpdateExpenseState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    new_description = message.text.strip()

    if not new_description:
        await message.answer("Опис не може бути порожнім. Введіть новий опис витрати:")
        return

    await state.update_data(new_description=new_description)

    await message.answer("Введіть нову суму витрати (в грн):")
    await state.set_state(UpdateExpenseState.waiting_for_price)

@dp.message(UpdateExpenseState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        new_price_uah = float(message.text.strip())
        if new_price_uah <= 0:
            await message.answer("Сума повинна бути більше нуля. Введіть коректну суму витрати:")
            return
    except ValueError:
        await message.answer("Сума повинна бути числом. Введіть коректну суму витрати:")
        return

    data = await state.get_data()
    expense_id = data.get("expense_id")
    new_description = data.get("new_description")

    async with aiohttp.ClientSession() as session:
        try:
            updated_expense = {
                "description": new_description,
                "price_uah": new_price_uah
            }
            async with session.put(f"{API_URL}/expenses/{expense_id}", json=updated_expense) as response:
                if response.status == 200:
                    await message.answer("Статтю витрат успішно оновлено.")
                else:
                    await message.answer(f"Не вдалося оновити витрату: {response.status}")
        except Exception as e:
            await message.answer(f"Помилка з’єднання з сервером: {e}")

    await state.clear()
    await message.answer("Ви повернулись до головного меню", reply_markup=await get_combined_kb())


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())