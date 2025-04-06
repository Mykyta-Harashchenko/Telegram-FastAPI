from aiogram.fsm.state import StatesGroup, State


class AddExpenseState(StatesGroup):
    name = State()
    date = State()
    price = State()

class ReportState(StatesGroup):
    start = State()
    end = State()

class DeleteExpenseState(StatesGroup):
    waiting_for_id = State()

class UpdateExpenseState(StatesGroup):
    waiting_for_id = State()
    waiting_for_description = State()
    waiting_for_price = State()

