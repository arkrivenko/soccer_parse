import json
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

headers = {
    'authority': 'soccer365.ru',
    'accept': '*/*',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    # 'cookie': 'PHPSESSID=qcpm552klgu0ihukate1lo8l26; device_type=1; _ga=GA1.1.1611811921.1687496999; _ga_YQ2WWHERLS=GS1.1.1689663126.38.1.1689663166.0.0.0',
    'referer': 'https://soccer365.ru/online/&date=2023-07-19',
    'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}


async def soccer_pre_bets_dict_maker(date_time_obj):
    while True:
        print(f"{date_time_obj}: начало нового цикла..")
        day_dict = {}
        # current_day = datetime.now().strftime("%Y-%m-%d")
        param_date = date_time_obj.strftime("%Y-%m-%d")
        next_day = date_time_obj.strftime("%d.%m")
        current_year = date_time_obj.strftime("%Y")
        params = {
            'c': 'live',
            'a': 'games_data',
            'competition_id': '0',
            'date': param_date,
            'vtp': '1',
        }

        response = requests.get('https://soccer365.ru/index.php', params=params, headers=headers)
        src = response.text
        soup = BeautifulSoup(src, "lxml")
        all_games = soup.find_all(class_="game_block")
        # print(f"Len all_games: {len(all_games)}")
        for game in all_games:
            try:
                date = game.find(class_="status").text.strip()
                if not date.startswith(next_day) or "Отменен" in date or "Перенесен" in date or "Остановлен" in date:
                    continue
                names = game.find(class_="game_link")["title"]
                game_link = "https://soccer365.ru" + game.find(class_="game_link")["href"]
                # print(f"\n{date}:\n{names}: {game_link}")
                game_page_response = requests.get(game_link, headers=headers)
                game_page_src = game_page_response.text
                game_soup = BeautifulSoup(game_page_src, "lxml")
                game_timer_raw = game_soup.find("div", {"id": "game_events"}).find("h2")
                if game_timer_raw:
                    game_timer = game_timer_raw.text.strip()
                    sym_index = game_timer.rindex(",") + 2
                    true_game_date = game_timer[sym_index:]
                else:
                    true_game_date = param_date
                odds_table = game_soup.find("div", {"id": "odds"})
                bet_dict = None
                if odds_table:
                    bet_dict = {}
                    odds_items = odds_table.find(class_="odds_item").find_all("div")
                    odds_items_list = [elem.text.strip() for elem in odds_items if elem.text][1:]
                    bet_companies = odds_table.find_all(class_="odds_logo")
                    for company in bet_companies:
                        company_data_elems = company.find_all("div")
                        company_data = [elem.text.strip() for elem in company_data_elems if elem.text]
                        company_dict = dict(zip(odds_items_list, company_data[1:]))
                        company_href_raw = company.find(class_="odds_title").find("a")
                        if company_href_raw:
                            company_href = company_href_raw["href"]
                            company_dict.update({"company_href": company_href})
                        final_company_dict = {company_data[0]: company_dict}
                        bet_dict.update(final_company_dict)
                if true_game_date.endswith(current_year):
                    timer_exists = False
                    game_started_soon_timer = None
                    game_pause_first_border = None
                    game_pause_second_border = None
                else:
                    timer_exists = True
                    game_started_soon_timer = str(datetime.strptime(true_game_date, "%d.%m.%Y %H:%M") -
                                                  timedelta(minutes=15))
                    game_pause_first_border = str(datetime.strptime(true_game_date, "%d.%m.%Y %H:%M") +
                                                  timedelta(minutes=45))
                    game_pause_second_border = str(datetime.strptime(true_game_date, "%d.%m.%Y %H:%M") +
                                                   timedelta(minutes=70))
                day_dict.update({names: {
                    "game_href": game_link,
                    "sent": False,
                    "game_play_time": true_game_date,
                    "game_started_soon_timer": game_started_soon_timer,
                    "game_pause_first_border": game_pause_first_border,
                    "game_pause_second_border": game_pause_second_border,
                    "timer_exists": timer_exists,
                    "game_started_soon": False,
                    "game_paused": False,
                    "bet_dicts": {"За день до игры": bet_dict},
                    "stats": None
                }})
            except Exception as ex:
                print(f"Pre dict maker error: {ex}")

        with open(f"bets/{next_day}_bets.json", "w", encoding="utf-8") as f:
            json.dump(day_dict, f, indent=4, ensure_ascii=False)

        date_time_obj += timedelta(days=1)
        date_time_at_end = datetime.now()
        seconds_to_wait = (date_time_obj - date_time_at_end).total_seconds()

        print(f"{date_time_at_end.strftime('%Y-%m-%d %H:%M:%S')}: цикл окончен, перехожу ко сну..")
        await asyncio.sleep(seconds_to_wait)


async def soccer_current_bets_dict_maker():
    datetime_now = datetime.now()

    current_day = datetime_now.strftime("%d.%m")
    next_day = datetime.strptime((datetime_now + timedelta(days=1)).strftime("%Y-%m-%d"), "%Y-%m-%d")

    with open(f"bets/{current_day}_bets.json", "r", encoding="utf-8") as f_read:
        games_dict = json.load(f_read)

    while True:
        games_to_sent_dict = {}
        current_day_raw = datetime.now()

        print(f"\n{current_day_raw}: сканирование сегодняшних игр..")
        for game_name, value in games_dict.items():
            game_href = value["game_href"]

            if value["timer_exists"]:
                game_play_time = datetime.strptime(value.get("game_play_time"), "%d.%m.%Y %H:%M")
                game_started_soon_timer = datetime.strptime(value.get("game_started_soon_timer"), "%Y-%m-%d %H:%M:%S")
                game_pause_first_border = datetime.strptime(value.get("game_pause_first_border"), "%Y-%m-%d %H:%M:%S")
                game_pause_second_border = datetime.strptime(value.get("game_pause_second_border"), "%Y-%m-%d %H:%M:%S")

            if value["timer_exists"] and not value["game_paused"] and not value["game_started_soon"] and \
                    game_started_soon_timer <= current_day_raw <= game_play_time:

                value["game_started_soon"] = True
                game_response = requests.get(game_href, headers=headers)
                game_src = game_response.text
                game_soup = BeautifulSoup(game_src, "lxml")
                odds_table = game_soup.find("div", {"id": "odds"})

                if odds_table:
                    bet_dict = {}
                    odds_items = odds_table.find(class_="odds_item").find_all("div")
                    odds_items_list = [elem.text.strip() for elem in odds_items if elem.text][1:]
                    bet_companies = odds_table.find_all(class_="odds_logo")

                    for company in bet_companies:
                        company_data_elems = company.find_all("div")
                        company_data = [elem.text.strip() for elem in company_data_elems if elem.text]
                        company_dict = dict(zip(odds_items_list, company_data[1:]))
                        company_href_raw = company.find(class_="odds_title").find("a")

                        if company_href_raw:
                            company_href = company_href_raw["href"]
                            company_dict.update({"company_href": company_href})
                        final_company_dict = {company_data[0]: company_dict}
                        bet_dict.update(final_company_dict)
                    value["bet_dicts"].update({"За 15 минут до игры": bet_dict})

            elif not value["game_paused"] and not value["game_started_soon"] and not value["timer_exists"]:
                game_response = requests.get(game_href, headers=headers)
                game_src = game_response.text
                game_soup = BeautifulSoup(game_src, "lxml")

                game_live_status = game_soup.find(class_="live_game_status")

                if game_live_status:
                    value["game_started_soon"] = True
                    odds_table = game_soup.find("div", {"id": "odds"})

                    if odds_table:
                        bet_dict = {}
                        odds_items = odds_table.find(class_="odds_item").find_all("div")
                        odds_items_list = [elem.text.strip() for elem in odds_items if elem.text][1:]
                        bet_companies = odds_table.find_all(class_="odds_logo")

                        for company in bet_companies:
                            company_data_elems = company.find_all("div")
                            company_data = [elem.text.strip() for elem in company_data_elems if elem.text]
                            company_dict = dict(zip(odds_items_list, company_data[1:]))
                            company_href_raw = company.find(class_="odds_title").find("a")

                            if company_href_raw:
                                company_href = company_href_raw["href"]
                                company_dict.update({"company_href": company_href})
                            final_company_dict = {company_data[0]: company_dict}
                            bet_dict.update(final_company_dict)
                        value["bet_dicts"].update({"За 15 минут до игры": bet_dict})

            elif value["timer_exists"] and not value["game_paused"] and value["game_started_soon"] and \
                    game_pause_first_border <= current_day_raw <= game_pause_second_border:

                game_response = requests.get(game_href, headers=headers)
                game_src = game_response.text
                game_soup = BeautifulSoup(game_src, "lxml")

                game_pause_flag = game_soup.find(class_="live_game_status")
                if game_pause_flag:
                    if game_pause_flag.text.strip() == "Перерыв":
                        value["game_paused"] = True
                        odds_table = game_soup.find("div", {"id": "odds"})

                        if odds_table:
                            bet_dict = {}
                            odds_items = odds_table.find(class_="odds_item").find_all("div")
                            odds_items_list = [elem.text.strip() for elem in odds_items if elem.text][1:]
                            bet_companies = odds_table.find_all(class_="odds_logo")

                            for company in bet_companies:
                                company_data_elems = company.find_all("div")
                                company_data = [elem.text.strip() for elem in company_data_elems if elem.text]
                                company_dict = dict(zip(odds_items_list, company_data[1:]))
                                company_href_raw = company.find(class_="odds_title").find("a")

                                if company_href_raw:
                                    company_href = company_href_raw["href"]
                                    company_dict.update({"company_href": company_href})
                                final_company_dict = {company_data[0]: company_dict}
                                bet_dict.update(final_company_dict)
                            value["bet_dicts"].update({"Во время перерыва": bet_dict})

                        game_stats = page_stats_reader(game_soup)
                        value["stats"] = game_stats

            elif not value["game_paused"] and value["game_started_soon"] and not value["timer_exists"]:
                game_response = requests.get(game_href, headers=headers)
                game_src = game_response.text
                game_soup = BeautifulSoup(game_src, "lxml")

                game_pause_flag = game_soup.find(class_="live_game_status")
                if game_pause_flag:
                    if game_pause_flag.text.strip() == "Перерыв":
                        value["game_paused"] = True
                        odds_table = game_soup.find("div", {"id": "odds"})

                        if odds_table:
                            bet_dict = {}
                            odds_items = odds_table.find(class_="odds_item").find_all("div")
                            odds_items_list = [elem.text.strip() for elem in odds_items if elem.text][1:]
                            bet_companies = odds_table.find_all(class_="odds_logo")

                            for company in bet_companies:
                                company_data_elems = company.find_all("div")
                                company_data = [elem.text.strip() for elem in company_data_elems if elem.text]
                                company_dict = dict(zip(odds_items_list, company_data[1:]))
                                company_href_raw = company.find(class_="odds_title").find("a")

                                if company_href_raw:
                                    company_href = company_href_raw["href"]
                                    company_dict.update({"company_href": company_href})
                                final_company_dict = {company_data[0]: company_dict}
                                bet_dict.update(final_company_dict)
                            value["bet_dicts"].update({"Во время перерыва": bet_dict})

                        game_stats = page_stats_reader(game_soup)
                        value["stats"] = game_stats

            if value["game_paused"] and not value["sent"]:

                games_to_sent_dict.update({game_name: value})
                # print(f"\n\nNew game to sent: {game_name}")
                value["sent"] = True

        with open(f"bets/{current_day}_bets.json", "w", encoding="utf-8") as f_bets:
            json.dump(games_dict, f_bets, indent=4, ensure_ascii=False)

        with open(f"games_to_sent.json", "w", encoding="utf-8") as f_games:
            json.dump(games_to_sent_dict, f_games, indent=4, ensure_ascii=False)

        if current_day_raw >= next_day:

            print(f"\nNew day: {current_day_raw}\n")

            current_day = current_day_raw.strftime("%d.%m")
            next_day = datetime.strptime((current_day_raw + timedelta(days=1)).strftime("%Y-%m-%d"), "%Y-%m-%d")

            with open(f"bets/{current_day}_bets.json", "r", encoding="utf-8") as f_read:
                games_dict = json.load(f_read)

        print(f"{datetime.now()}: сканирование окончено, засыпаю..")

        await asyncio.sleep(150)


def page_stats_reader(soup):
    stats_data = None
    table = soup.find("div", id="stats")
    stats_columns = table.find_all(class_="stats_items")

    if stats_columns:
        try:
            kicks_data, kicks_on_target_data, attacks_data, danger_attacks_data, violations_data, yellow_cards_data = \
                "", "", "", "", "", ""

            for item in stats_columns:
                all_titles = item.find_all(class_="stats_item")
                for title in all_titles:
                    if title.find(class_="stats_title").text == "Удары":
                        kicks = title.find_all(class_="stats_inf")
                        kicks_data = "-".join([kicks[0].text, kicks[1].text])

                    if title.find(class_="stats_title").text == "Удары в створ":
                        kicks_on_target = title.find_all(class_="stats_inf")
                        kicks_on_target_data = "-".join([kicks_on_target[0].text, kicks_on_target[1].text])

                    if title.find(class_="stats_title").text == "Атаки":
                        attacks = title.find_all(class_="stats_inf")
                        attacks_data = "-".join([attacks[0].text, attacks[1].text])

                    if title.find(class_="stats_title").text == "Опасные атаки":
                        attacks = title.find_all(class_="stats_inf")
                        danger_attacks_data = "-".join([attacks[0].text, attacks[1].text])
                        break

                    if title.find(class_="stats_title").text == "Нарушения":
                        violations = title.find_all(class_="stats_inf")
                        violations_data = "-".join([violations[0].text, violations[1].text])
                        break

                    if title.find(class_="stats_title").text == "Желтые карточки":
                        yellow_cards = title.find_all(class_="stats_inf")
                        yellow_cards_data = "-".join([yellow_cards[0].text, yellow_cards[1].text])

            both_kicks = kicks_data.split("-")
            both_kicks_sum = 0
            for elem in both_kicks:
                if elem.isdigit():
                    both_kicks_sum += int(elem)
            both_kicks_on_target = kicks_on_target_data.split("-")
            both_kicks_on_target_sum = 0
            for elem in both_kicks_on_target:
                if elem.isdigit():
                    both_kicks_on_target_sum += int(elem)
            both_attacks = attacks_data.split("-")
            both_attacks_sum = 0
            for elem in both_attacks:
                if elem.isdigit():
                    both_attacks_sum += int(elem)
            both_danger_attacks_sum = 0
            for elem in danger_attacks_data:
                if elem.isdigit():
                    both_danger_attacks_sum += int(elem)
            both_violations = violations_data.split("-")
            both_violations_sum = 0
            for elem in both_violations:
                if elem.isdigit():
                    both_violations_sum += int(elem)
            both_yellow_cards = yellow_cards_data.split("-")
            both_yellow_cards_sum = 0

            for elem in both_yellow_cards:
                if elem.isdigit():
                    both_yellow_cards_sum += int(elem)

            refs_dict = ""
            referees_table = soup.find_all(class_="preview_item")

            if referees_table:
                referees_dict = {}
                for finder in referees_table:
                    r_title = finder.find(class_="preview_param").text.strip()
                    if r_title == "Арбитры":
                        referees = finder.find_all("div")
                        if referees:
                            for referee in referees:
                                referee_name = referee.find("span").text.strip()
                                if referee_name not in referees_dict:
                                    referee_href = "https://soccer365.ru" + referee.find("a")["href"]
                                    referee_dict = {referee_name: referee_href}
                                    referees_dict.update(referee_dict)
                        separators = finder.find_all(class_="preview_sep")

                        if separators:
                            for separator in separators:
                                another_referee = separator.next_sibling.text.strip()
                                if another_referee and another_referee not in referees_dict:
                                    referee_dict = {another_referee: ""}
                                    referees_dict.update(referee_dict)
                        if not referees and not separators:
                            row_referee_name = finder.text.strip()
                            dot_index = row_referee_name.index("ы") + 1
                            referee_name = row_referee_name[dot_index:].strip()
                            if referee_name not in referees_dict:
                                referee_dict = {referee_name: ""}
                                referees_dict.update(referee_dict)
                        finder_text = finder.text.strip()
                        if "ы" in finder_text and "|" in finder_text:
                            first_index = finder_text.index("ы") + 1
                            second_index = finder_text.index("|")
                            first_name = finder_text[first_index:second_index].strip()
                            if first_name not in referees_dict:
                                referee_dict = {first_name: ""}
                                referees_dict.update(referee_dict)

                if referees_dict:
                    # print(f"dict: {referees_dict}")
                    referees_list = []
                    for key, value in referees_dict.items():
                        # print(f"key: {key}, value: {value}")
                        if value:
                            r_response = requests.get(value, headers=headers)
                            r_src = r_response.text
                            r_soup = BeautifulSoup(r_src, "lxml")
                            profile_title = r_soup.find(class_="profile_info_title").text.strip()
                            alternative_name_flag = r_soup.find(class_="profile_en_title")
                            if alternative_name_flag:
                                alternative_name = alternative_name_flag.text.strip()
                                referees_list.append(alternative_name)
                            else:
                                referees_list.append(profile_title)
                        else:
                            profile_title = key
                            # print(f"name: {profile_title}")
                            referees_list.append(profile_title)
                    # print(f"referees list: {referees_list}")
                    refs_dict = referee_finder(referees_list)
                    # print(f"refs dict: {refs_dict}")

            scores = soup.find_all(class_="live_game_goal")
            final_scores = "-".join([scores[0].text.strip(), scores[1].text.strip()])

            stats_data = {
                "score": final_scores,
                "kicks": {"sum": both_kicks_sum,
                          "data": kicks_data},
                "t_kicks": {"sum": both_kicks_on_target_sum,
                            "data": kicks_on_target_data},
                "attacks": {"sum": both_attacks_sum,
                            "data": attacks_data},
                "danger_attacks": {"sum": both_danger_attacks_sum,
                                   "data": danger_attacks_data},
                "violations": {"sum": both_violations_sum,
                               "data": violations_data},
                "yellow_cards": {"sum": both_yellow_cards_sum,
                                 "data": yellow_cards_data},
                "refs": refs_dict
            }

        except Exception as ex:
            print(f"{datetime.now()}. page_stats_reader error:\n{ex}")

        finally:
            return stats_data


def referee_finder(referees_list):
    if referees_list:
        refs_final_dict = {}
        if len(referees_list) > 1:
            for referee_name in referees_list:
                if type(referee_name) == list:
                    for name in referee_name:
                        name_dict = name_checker(name)
                        if name_dict:
                            refs_final_dict.update(name_dict)
                            break
                else:
                    name_dict = name_checker(referee_name)
                    if name_dict:
                        refs_final_dict.update(name_dict)
        else:
            if type(referees_list[0]) == list:
                for name in referees_list[0]:
                    name_dict = name_checker(name)
                    if name_dict:
                        refs_final_dict.update(name_dict)
                        break
            else:
                name_dict = name_checker(referees_list[0])
                if name_dict:
                    refs_final_dict.update(name_dict)

        return refs_final_dict


def name_checker(referee_name):
    ref_dict_elem = ""
    short_name_flag = referee_name.split()
    dot_flag = False
    if short_name_flag[0].endswith("."):
        referee_name = short_name_flag[1]
        first_letter = short_name_flag[0][0]
        dot_flag = True
    ref_params = {
        'query': referee_name,
    }

    response = requests.get('https://4score.ru/referee/search/', params=ref_params, headers=headers)
    src = response.text
    soup = BeautifulSoup(src, "lxml")
    urls_flag = soup.find(class_="display")
    if urls_flag:
        urls = urls_flag.find_all("a")
        href = ""
        for url in urls:
            name = url.find("span").text.strip()
            if name == referee_name:
                href = "https://4score.ru" + url["href"]
                break
            alternative_name_flag = url.find(class_="sf-gray")
            if alternative_name_flag:
                alternative_name = alternative_name_flag.text.strip()
                if alternative_name == referee_name:
                    href = "https://4score.ru" + url["href"]
                    break
            if dot_flag:
                if referee_name in name and name.startswith(first_letter):
                    href = "https://4score.ru" + url["href"]
                    break
                if alternative_name_flag and referee_name in alternative_name and \
                        alternative_name.startswith(first_letter):
                    href = "https://4score.ru" + url["href"]
                    break

        if href:
            referee_stats_page_response = requests.get(href, headers=headers)
            n_src = referee_stats_page_response.text
            n_soup = BeautifulSoup(n_src, "lxml")
            stats_table = n_soup.find(class_="row param-thumbs")
            if stats_table:
                stats_data = stats_table.find_all(class_="param-thumb")
                ref_dict_elem = {referee_name: []}
                for stat in stats_data:
                    s_title = stat.find(class_="param-thumb-name").text.strip()
                    s_value = stat.find(class_="param-thumb-value").text.strip()
                    stat_line = ": ".join([s_title, s_value])
                    ref_dict_elem[referee_name].append(stat_line)
    return ref_dict_elem
