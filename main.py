import logging
import os
import pandas as pd
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
log_file = "bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# Константы
API_TOKEN = "---"
DATA_FILES = {
    "Цех 1": "workshop 1.xlsx",
    "Цех 2": "workshop 2.xlsx",
    "Цех 3": "workshop 3.xlsx",
    "Цех 4": "workshop 4.xlsx",
}

# Состояния
class UserStates(StatesGroup):
    waiting_for_workshop = State()
    waiting_for_machine = State()

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура для выбора цеха
def create_workshop_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=name)] for name in DATA_FILES.keys()
        ]
    )

# Клавиатура для возврата назад
def create_back_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_workshop")]
        ]
    )

# Команда старт
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_workshop)
    await message.reply(
        "Добро пожаловать в бота-информатора по машинам.\nВыберите интересующий вас цех:",
        reply_markup=create_workshop_keyboard(),
    )
    logger.info(f"Пользователь {message.from_user.id} начал работу.")

# Выбор цеха
@dp.callback_query(lambda call: call.data in DATA_FILES.keys())
async def choise_workshop(call: types.CallbackQuery, state: FSMContext):
    workshop = call.data
    data_file = DATA_FILES[workshop]

    # Проверка существования файла
    if not os.path.exists(data_file):
        await call.message.edit_text(f"Файл {data_file} не найден.", reply_markup=create_back_button())
        logger.error(f"Файл {data_file} не найден.")
        return

    # Чтение файла
    try:
        df = pd.read_excel(data_file)
    except Exception as e:
        await call.message.edit_text("Ошибка чтения файла. Попробуйте позже.", reply_markup=create_back_button())
        logger.error(f"Ошибка чтения файла {data_file}: {e}")
        return

    # Проверка наличия столбца 'Машина'
    if "Машина" not in df.columns:
        await call.message.edit_text("В файле отсутствует столбец 'Машина'.", reply_markup=create_back_button())
        logger.error(f"В файле {data_file} отсутствует столбец 'Машина'.")
        return

    # Создание клавиатуры для выбора машин
    machines = df["Машина"].dropna().tolist()
    machine_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=machine, callback_data=machine)] for machine in machines
        ] + [[InlineKeyboardButton(text="Назад", callback_data="back_to_workshop")]]
    )

    # Установка состояния и отправка сообщения
    await state.update_data(workshop=workshop)
    await state.set_state(UserStates.waiting_for_machine)
    await call.message.edit_text("Выберите машину:", reply_markup=machine_keyboard)
    logger.info(f"Пользователь {call.from_user.id} выбрал цех: {workshop}")

# Выбор машины
@dp.callback_query(lambda call: call.data not in DATA_FILES.keys() and call.data != "back_to_workshop")
async def machine_choise(call: types.CallbackQuery, state: FSMContext):
    machine = call.data

    try:
        with open("Machine_info.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if line.strip() == machine:
                    info = ""
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() == "<":  # Разделитель между машинами
                            break
                        info += lines[j]
                    # Отправка информации о машине
                    await call.message.edit_text(
                        f"<b>Информация о машине {machine}:</b>\n{info}",
                        parse_mode="HTML",
                        reply_markup=create_back_button(),
                    )
                    return
            # Если машина не найдена
            await call.message.edit_text(
                f"Информация о машине {machine} не найдена.",
                reply_markup=create_back_button(),
            )
    except Exception as e:
        await call.message.edit_text("Ошибка при обработке информации о машине.", reply_markup=create_back_button())
        logger.error(f"Ошибка при чтении файла с информацией о машинах: {e}")

# Кнопка назад
@dp.callback_query(lambda call: call.data == "back_to_workshop")
async def back_to_workshop(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_workshop)
    await call.message.edit_text("Выберите цех:", reply_markup=create_workshop_keyboard())

# Запуск бота
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())