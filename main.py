import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'X-Requested-With': 'XMLHttpRequest',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://soccer365.ru/online/',
    # 'Cookie': 'PHPSESSID=sfch1atbor87lsoprf30svl5ru; device_type=1',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    # Requests doesn't support trailers
    # 'TE': 'trailers',
}

params = {
    'c': 'live',
    'a': 'games_data',
    'competition_id': '0',
    'date': '',
    'vtp': '1',
}


def collect_games(c_kicks, c_kicks_on_target, c_attacks, c_violations, c_yellow_cards, processed_matches):
    print(f"\n{datetime.now()}: starting a circle..")
    # print("Page parse..")
    zero_plays = []
    response = requests.get('https://soccer365.ru/index.php', params=params, headers=headers)
    src = response.text
    soup = BeautifulSoup(src, "lxml")
    all_games = soup.find_all(class_="game_block online")

    for game in all_games:
        play_time = game.find(class_="status").text.strip()

        if not play_time == "Перерыв":
            continue

        # scores = game.find(class_="result").find_all(class_="gls")

        # if scores[0].text != "0" or scores[1].text != "0":
        #     continue

        href = "https://soccer365.ru" + game.find("a")["href"]
        title = game.find("a")["title"]

        if title in processed_matches:
            continue

        print(f"Href: {href}, title: {title}, play time: {play_time}")
        game_data = [title, play_time, href]
        zero_plays.append(game_data)
    game_page_reader(zero_plays, c_kicks, c_kicks_on_target, c_attacks, c_violations, c_yellow_cards)


def game_page_reader(zero_plays, c_kicks, c_kicks_on_target, c_attacks, c_violations, c_yellow_cards):
    stats_data = []
    if zero_plays:
        for game in zero_plays:
            href = game[2]
            req = requests.get(href, headers=headers)
            src = req.text
            soup = BeautifulSoup(src, "lxml")

            table = soup.find("div", id="stats")
            stats_columns = table.find_all(class_="stats_items")

            if stats_columns:
                # try:
                    kicks_data, kicks_on_target_data, attacks_data, violations_data, yellow_cards_data = \
                        "", "", "", "", ""

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

                    if both_kicks_sum < int(c_kicks):
                        continue
                    elif both_kicks_on_target_sum < int(c_kicks_on_target):
                        continue
                    elif both_attacks_sum < int(c_attacks):
                        continue
                    elif both_violations_sum < int(c_violations):
                        continue
                    elif both_yellow_cards_sum < int(c_yellow_cards):
                        continue
                    else:
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

                        stats_data.append(
                            {
                                "title": game[0],
                                "score": final_scores,
                                "time": game[1],
                                "url": game[2],
                                "kicks": kicks_data,
                                "t_kicks": kicks_on_target_data,
                                "attacks": attacks_data,
                                "violations": violations_data,
                                "yellow_cards": yellow_cards_data,
                                "refs": refs_dict
                            }
                        )

                # except Exception as ex:
                #     print(ex)

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(stats_data, f, indent=4, ensure_ascii=False)


def referee_finder(referees_list):
    print(f"list: {referees_list}")
    print(f"len: {len(referees_list)}")
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
    print(f"Referee name: {referee_name}")
    # print(f"finder func r_name: {referee_name}")
    short_name_flag = referee_name.split()
    dot_flag = False
    if short_name_flag[0].endswith("."):
        referee_name = short_name_flag[1]
        first_letter = short_name_flag[0][0]
        # print(first_letter)
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
            # print(f"name: {name}")
            if name == referee_name:
                href = "https://4score.ru" + url["href"]
                break
            alternative_name_flag = url.find(class_="sf-gray")
            if alternative_name_flag:
                alternative_name = alternative_name_flag.text.strip()
                # print(f"alternative: {alternative_name}")
                if alternative_name == referee_name:
                    href = "https://4score.ru" + url["href"]
                    break
            if dot_flag:
                # print("dot flag")
                if referee_name in name and name.startswith(first_letter):
                    href = "https://4score.ru" + url["href"]
                    break
                if alternative_name_flag and referee_name in alternative_name and \
                        alternative_name.startswith(first_letter):
                    href = "https://4score.ru" + url["href"]
                    break
            # else:
            #     alternative_name = "отсутствует"
            # print(f"\nhref: {href}, name: {name}, alternative: {alternative_name}")
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
