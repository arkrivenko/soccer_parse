from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.markdown import hbold, hlink
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime, timedelta
import json
import time
import asyncio
import logging

from pre_data import soccer_pre_bets_dict_maker, soccer_current_bets_dict_maker
from security import TOKEN


bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

running = {}


class UserState(StatesGroup):
    danger_attacks = State()
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
    await message.answer("Введите минимальный показатель опасных атак")
    await UserState.danger_attacks.set()


@dp.message_handler(Text(equals="Отмена"))
async def cmd_cancel(message: types.Message):
    running[message.from_user.id] = False
    await message.answer("Поиск будет остановлен..")


@dp.message_handler(state=UserState.danger_attacks)
async def attacks_set(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(danger_attacks=message.text)
    await message.answer("Введите минимальный показатель нарушений")
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
    danger_attacks = data.get('danger_attacks')
    violations = data.get('violations')
    yellow_cards = data.get('yellow_cards')
    await state.finish()
    await message.answer(f"Указаны следующих показатели для фильтрации игр:\n"
                         f"{hbold('Опасные атаки: ')}{danger_attacks}\n"
                         f"{hbold('Нарушения: ')}{violations}\n"
                         f"{hbold('Желтые карточки: ')}{yellow_cards}\n\n"
                         f"Приступаю к поиску..")

    sent_games = {}

    running[message.from_user.id] = True
    while running.get(message.from_user.id):

        with open("games_to_sent.json", encoding="utf-8") as f:
            games_to_sent = json.load(f)

        if games_to_sent:

            for game, value in games_to_sent.items():
                if not value.get('stats'):
                    continue

                if game in sent_games:
                    datetime_now = datetime.now()
                    del_flag_time = sent_games[game] + timedelta(minutes=30)
                    if del_flag_time < datetime_now:
                        del sent_games[game]
                    continue

                if value.get('stats').get("danger_attacks").get("sum") >= int(danger_attacks) or \
                        value.get('stats').get("violations").get("sum") >= int(violations) or \
                        value.get('stats').get("yellow_cards").get("sum") >= int(yellow_cards):

                    kicks_data = value.get('stats').get('kicks').get('data')
                    t_kicks_data = value.get('stats').get('t_kicks').get('data')
                    attacks_data = value.get('stats').get('attacks').get('data')
                    danger_attacks_data = value.get('stats').get('danger_attacks').get('data')
                    violations_data = value.get('stats').get('violations').get('data')
                    yellow_cards_data = value.get('stats').get('yellow_cards').get('data')
                    card = f"{hlink(game, value.get('game_href'))}\n" \
                           f"{hbold('Счёт: ')}{value.get('stats').get('score')}\n" \
                           f"{hbold('Удары: ')}{kicks_data or 'данные отсутствуют'}\n" \
                           f"{hbold('Удары в створ: ')}{t_kicks_data or 'данные отсутствуют'}\n" \
                           f"{hbold('Атаки: ')}{attacks_data or 'данные отсутствуют'}\n" \
                           f"{hbold('Опасные атаки: ')}{danger_attacks_data or 'данные отсутствуют'}\n" \
                           f"{hbold('Нарушения: ')}{violations_data or 'данные отсутствуют'}\n" \
                           f"{hbold('Желтые карточки: ')}{yellow_cards_data or 'данные отсутствуют'}\n"

                    referees_data = value.get('stats').get('refs')
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

                    bets_data = value.get('bet_dicts')
                    bet_card = ""

                    if bets_data:

                        bets_dict = {}
                        for key, b_value in bets_data.items():
                            if not b_value:
                                continue

                            for bet_name, bet_value in b_value.items():
                                bet_href = bet_value.get("company_href")
                                bid_keys = list(bet_value.keys())
                                bid_values = list(bet_value.values())
                                if "company_href" in bid_keys:
                                    bid_keys = bid_keys[:-1]
                                    bid_values = bid_values[:-1]
                                if bet_name not in bets_dict:
                                    bets_dict.update({bet_name: {
                                        "bet_href": bet_href,
                                        "bet_periods": [key],
                                        "bid_data": [bid_keys, bid_values],
                                    }})

                                else:
                                    if not bets_dict[bet_name]["bet_href"] and bet_href:
                                        bets_dict[bet_name]["bet_href"] = bet_href
                                    bets_dict[bet_name]["bet_periods"].append(key)
                                    bets_dict[bet_name]["bid_data"].append(bid_values)

                        if bets_dict:
                            for bet_company_title, bet_value in bets_dict.items():
                                bet_href = bet_value["bet_href"]
                                bet_periods = bet_value["bet_periods"]
                                if len(bet_periods) > 1:
                                    bet_periods_str = "; ".join(bet_periods)
                                else:
                                    bet_periods_str = bet_periods[0]
                                if bet_href:
                                    bet_company_name = f"{hlink(bet_company_title, bet_href)}\n({bet_periods_str})"
                                else:
                                    bet_company_name = f"{hbold(bet_company_title)}\n({bet_periods_str})"
                                data_lists = bet_value["bid_data"]
                                list_to_sent = list(zip(*data_lists))
                                for line in list_to_sent:
                                    str_line = ""
                                    for count, elem in enumerate(line):
                                        if count == 0:
                                            if "ТМ" in elem:
                                                str_line = "".join([str_line, f"{elem:<8}"])
                                            elif "ТБ" in elem:
                                                str_line = "".join([str_line, f"{elem:<9}"])
                                            else:
                                                str_line = "".join([str_line, f"{elem:<13}"])
                                        else:
                                            str_line = "".join([str_line, f"{elem:<10}"])

                                    bet_company_name = "\n".join([bet_company_name, str_line])
                                bet_card = "\n\n".join([bet_card, bet_company_name])

                    time.sleep(2)

                    try:
                        await message.answer(card)

                        if bet_card:
                            await message.answer(bet_card)

                        sent_games.update({game: datetime.now()})

                    except Exception as ex:
                        print(f"Bot answer error: {ex}")

        await asyncio.sleep(90)


async def on_startup(dp: Dispatcher):
    next_day = datetime.now().date() + timedelta(days=1)
    edited_next_day = str(next_day) + " 16:00:00"
    date_time_start_obj = datetime.strptime(edited_next_day, "%Y-%m-%d %H:%M:%S")
    asyncio.create_task(soccer_pre_bets_dict_maker(date_time_start_obj))
    asyncio.create_task(soccer_current_bets_dict_maker())


def main():
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
