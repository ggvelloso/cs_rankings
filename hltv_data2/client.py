import abc

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


class CSRankingsClient(abc.ABC):
    def __init__(self):
        options = self._get_default_options()
        self.driver = webdriver.Chrome(options=options)
        self.ranking_url = ""

    @staticmethod
    def _get_default_options():
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x720")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.headless = False
        return options

    def _get_page_source(self, url, nr_retries=1):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10)
            import time  #TODO test if this is really needed for ESL pulls..
            time.sleep(10)
            return self.driver.page_source
        except Exception as e:
            print(f"Error occurred while fetching URL: {url}")
            print(f"Error details: {e}")
            if nr_retries == 1:
                return None
            print(f"Retrying... ({nr_retries-1} left)")
            return self._get_page_source(url, nr_retries=nr_retries-1)

    @abc.abstractmethod
    def get_ranking(self):
        pass

    def close(self):
        self.driver.quit()


class HLTVRankings(CSRankingsClient):

    def __init__(self):
        super().__init__()
        BASE_URL = "https://www.hltv.org"
        self.ranking_url = f"{BASE_URL}/ranking/teams"

    def get_ranking(self):
        ranking = []
        page_source = self._get_page_source(self.ranking_url)
        if page_source:
            soup = BeautifulSoup(page_source, "html.parser")
            teams = soup.find_all("div", {"class": "ranked-team"})
            for team in teams:
                position = team.find("span", {"class": "position"}).text.strip()[1:]
                name = (
                    team.find("div", {"class": "teamLine"})
                    .find("span", {"class": "name"})
                    .text.strip()
                )
                points = (
                    team.find("div", {"class": "teamLine"})
                    .find("span", {"class": "points"})
                    .text.strip()[1:-1]
                    .split(" ")[0]
                )
                ranking_item = {
                    "position": int(position),
                    "name": name,
                    "points": int(points),
                }
                ranking.append(ranking_item)

        self.close()  # TODO experiment with moving in get_page_source
        return ranking


class ValveLiveRankings(HLTVRankings):

    def __init__(self):
        super().__init__()
        BASE_URL = "https://www.hltv.org"
        self.ranking_url = f"{BASE_URL}/valve-ranking/teams"


class ESLRankings(CSRankingsClient):

    def __init__(self):
        super().__init__()
        self.ranking_url = "https://pro.eslgaming.com/worldranking/csgo/rankings/"

    def get_ranking(self):
        ranking = []
        page_source = self._get_page_source(self.ranking_url)

        if page_source:
            soup = BeautifulSoup(page_source, "html.parser")
            teams = soup.select("div[class*=RankingsTeamItem__Row-]")

            rank, points, teamname = [], [], []
            for team in teams:
                try:  # First pull all numbers; in case of no error, add them all to the running lists
                    this_pt = int(team.select('div[class*=Points]')[0].find("span").next.strip())
                    this_name = str(team.select('div[class*=TeamName]')[0].select('a[class]')[0].next)
                    this_rank = int(team.select('span[class*=WorldRankBadge__Number]')[0].next)
                    points.append(this_pt)
                    teamname.append(this_name)
                    rank.append(this_rank)
                except TypeError as e:  # TODO this currently only happens for team with 0.5 points
                    print('Not succeeded: ', team, e)
            ranking = [{'position': rank[i], 'name': teamname[i], 'points': points[i]} for i in range(len(points))]  # TODO: refactor, but first try to see if it works

        self.close()  # TODO experiment with moving in get_page_source
        return ranking