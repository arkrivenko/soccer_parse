import json
import requests
from bs4 import BeautifulSoup

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
zero_plays = []


def collect_games(c_kicks, c_kicks_on_target, c_attacks, c_danger_attacks):
    print("Page parse..")
    response = requests.get('https://soccer365.ru/index.php', params=params, headers=headers)
    src = response.text
    soup = BeautifulSoup(src, "lxml")
    all_games = soup.find_all(class_="game_block online")

    for game in all_games:
        play_time = game.find(class_="status").text.strip()

        if not play_time == "Перерыв":
            continue

        scores = game.find(class_="result").find_all(class_="gls")

        if scores[0].text != "0" or scores[1].text != "0":
            continue

        href = "https://soccer365.ru" + game.find("a")["href"]
        title = game.find("a")["title"]

        print(f"Href: {href}, title: {title}, play time: {play_time}")
        game_data = [title, play_time, href]
        zero_plays.append(game_data)
    game_page_reader(c_kicks, c_kicks_on_target, c_attacks, c_danger_attacks)


def game_page_reader(c_kicks, c_kicks_on_target, c_attacks, c_danger_attacks):
    global zero_plays
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
                try:
                    kicks_data, kicks_on_target_data, attacks_data, danger_attacks_data = "", "", "", ""

                    for item in stats_columns:
                        all_titles = item.find_all(class_="stats_item")
                        for title in all_titles:
                            if title.find(class_="stats_title").text == "Удары":
                                kicks = title.find_all(class_="stats_inf")
                                kicks_data = "-".join([kicks[0].text, kicks[1].text])

                            if title.find(class_="stats_title").text == "Удары в створ":
                                kicks_on_target = title.find_all(class_="stats_inf")
                                kicks_on_target_data = "-".join([kicks_on_target[0].text, kicks_on_target[1].text])
                                break

                            if title.find(class_="stats_title").text == "Атаки":
                                attacks = title.find_all(class_="stats_inf")
                                attacks_data = "-".join([attacks[0].text, attacks[1].text])

                            if title.find(class_="stats_title").text == "Опасные атаки":
                                danger_attacks = title.find_all(class_="stats_inf")
                                danger_attacks_data = "-".join([danger_attacks[0].text, danger_attacks[1].text])
                                break

                    both_kicks = kicks_data.split("-")
                    both_kicks_sum = 0
                    for elem in both_kicks:
                        both_kicks_sum += int(elem)
                    both_kicks_on_target = kicks_on_target_data.split("-")
                    both_kicks_on_target_sum = 0
                    for elem in both_kicks_on_target:
                        both_kicks_on_target_sum += int(elem)
                    both_attacks = attacks_data.split("-")
                    both_attacks_sum = 0
                    for elem in both_attacks:
                        both_attacks_sum += int(elem)
                    both_danger_attacks = danger_attacks_data.split("-")
                    both_danger_attacks_sum = 0
                    for elem in both_danger_attacks:
                        both_danger_attacks_sum += int(elem)

                    if both_kicks_sum < int(c_kicks):
                        continue
                    elif both_kicks_on_target_sum < int(c_kicks_on_target):
                        continue
                    elif both_attacks_sum < int(c_attacks):
                        continue
                    elif both_danger_attacks_sum < int(c_danger_attacks):
                        continue
                    else:

                        stats_data.append(
                            {
                                "title": game[0],
                                "time": game[1],
                                "url": game[2],
                                "kicks": kicks_data,
                                "t_kicks": kicks_on_target_data,
                                "attacks": attacks_data,
                                "danger_attacks": danger_attacks_data
                            }
                        )

                except Exception as ex:
                    print(ex)

    with open("result.json", "w") as f:
        json.dump(stats_data, f, indent=4, ensure_ascii=False)
