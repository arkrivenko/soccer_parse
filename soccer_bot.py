from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.markdown import hbold, hlink
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from security import TOKEN
from datetime import datetime, timedelta
from main import collect_games
import json
import time
import asyncio

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

running = {}


class UserState(StatesGroup):
    kicks = State()
    kicks_on_target = State()
    attacks = State()
    violations = State()
    yellow_cards = State()


@dp.message_handler(commands='start')
async def start(message: types.Message):
    search_buttons = ("⚽ поиск матчей", "Отмена")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in search_buttons:
        keyboard.add(button)
    await message.answer("Для запуска поиска подходящих игр нажмите на кнопку ⤵️", reply_markup=keyboard)


@dp.message_handler(Text(equals='⚽ поиск матчей'))
async def user_configs(message: types.Message):
    await message.answer("Введите минимальный показатель ударов")
    await UserState.kicks.set()


# @dp.message_handler(Text(equals='Проверка'))
# async def user_configs(message: types.Message):
#     words_list = ["Hi", "there", "mine", "friend"]
#     for word in words_list:
#         await bot.send_message(message.from_user.id, word)


@dp.message_handler(Text(equals="Отмена"))
async def cmd_cancel(message: types.Message):
    running[message.from_user.id] = False
    await message.answer("Поиск будет остановлен..")


@dp.message_handler(state=UserState.kicks)
async def kicks_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(kicks=message.text)
    await message.answer("Введите минимальный показатель ударов в створ")
    await UserState.next()


@dp.message_handler(state=UserState.kicks_on_target)
async def kicks_on_target_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(kicks_on_target=message.text)
    await message.answer("Введите минимальный показатель нарушений")
    await UserState.next()


@dp.message_handler(state=UserState.attacks)
async def attacks_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(attacks=message.text)
    await message.answer("Введите минимальный показатель опасных атак")
    await UserState.next()


@dp.message_handler(state=UserState.violations)
async def violations_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(violations=message.text)
    await message.answer("Введите показатель желтых карточек")
    await UserState.next()


@dp.message_handler(state=UserState.yellow_cards)
async def yellow_cards_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(yellow_cards=message.text)
    data = await state.get_data()
    kicks = data.get('kicks')
    kicks_on_target = data.get('kicks_on_target')
    attacks = data.get('attacks')
    violations = data.get('violations')
    yellow_cards = data.get('yellow_cards')
    await state.finish()
    await message.answer(f"Указаны следующих показатели для фильтрации игр:\n"
                         f"{hbold('Удары: ')}{kicks}\n"
                         f"{hbold('Удары в створ: ')}{kicks_on_target}\n"
                         f"{hbold('Атаки: ')}{attacks}\n"
                         f"{hbold('Нарушения: ')}{violations}\n"
                         f"{hbold('Желтые карточки: ')}{yellow_cards}\n\n"
                         f"Приступаю к поиску..")

    processed_matches = {}
    checkout_time = timedelta(hours=2)
    running[message.from_user.id] = True
    while running.get(message.from_user.id):
        # print("\nStarting a circle..")
        collect_games(kicks, kicks_on_target, attacks, violations, yellow_cards, processed_matches)

        with open("result.json") as f:
            stats_data = json.load(f)

        if stats_data:
            for index, game in enumerate(stats_data):

                card = f"{hlink(game.get('title'), game.get('url'))}\n" \
                       f"{hbold('Счёт: ')}{game.get('score')}\n" \
                       f"{hbold('Время: ')}{game.get('time')}\n" \
                       f"{hbold('Удары: ')}{game.get('kicks') or 'данные отсутствуют'}\n" \
                       f"{hbold('Удары в створ: ')}{game.get('t_kicks') or 'данные отсутствуют'}\n" \
                       f"{hbold('Атаки: ')}{game.get('attacks') or 'данные отсутствуют'}\n" \
                       f"{hbold('Нарушения: ')}{game.get('violations') or 'данные отсутствуют'}\n" \
                       f"{hbold('Желтые карточки: ')}{game.get('yellow_cards') or 'данные отсутствуют'}\n"

                referees_data = game.get('refs')
                if referees_data:
                    final_ref_line = "Данные по арбитрам: "
                    for referee in referees_data:
                        # print(f"Referee: {referee}")
                        ref_line = f"{hbold(referee)}"
                        referee_stats = referees_data[referee]
                        for stat in referee_stats:
                            # print(f"stat: {stat}")
                            ref_line = "\n".join([ref_line, stat])
                        final_ref_line = "\n\n".join([final_ref_line, ref_line])

                    # print(f"final ref line: {final_ref_line}")
                    card = "\n\n".join([card, final_ref_line])

                processed_matches[game.get('title')] = datetime.now()

                if index % 10 == 0:
                    time.sleep(3)

                await message.answer(card)

            if processed_matches:
                for key, value in processed_matches.copy().items():
                    now = datetime.now()
                    if now - value >= checkout_time:
                        del processed_matches[key]

        await asyncio.sleep(240)


def main():
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    main()
