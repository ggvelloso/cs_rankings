import abc
import os
import shutil

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class CSRankings(abc.ABC):

    @abc.abstractmethod
    def get_ranking(self):
        pass


class CSRankingsClient(CSRankings, abc.ABC):
    def __init__(self):
        options = self._get_default_options()
        self.driver = webdriver.Chrome(options=options)
        self.ranking_url = ""

    @staticmethod
    def _get_default_options():
        options = Options()
        options.add_argument("--disable-search-engine-choice-screen")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.headless = False
        return options

    def _get_page_source(self, url, nr_retries=1, explicit_wait=True):
        try:
            self.driver.get(url)
            if explicit_wait:
                import time
                time.sleep(3)
            else:
                self.driver.implicitly_wait(10)
            return self.driver.page_source
        except Exception as e:
            print(f"Error occurred while fetching URL: {url}")
            print(f"Error details: {e}")
            if nr_retries == 1:
                return None
            print(f"Retrying... ({nr_retries-1} left)")
            return self._get_page_source(url, nr_retries=nr_retries-1)

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
                players = ([x.text for x in
                            team.find("div", {"class": "playersLine"})
                            .find_all("span")])
                ranking_item = {
                    "position": int(position),
                    "name": name,
                    "points": int(points),
                    "players": players
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

    def __init__(self, round_half_down=True):
        super().__init__()
        self.ranking_url = "https://pro.eslgaming.com/worldranking/csgo/rankings/"
        self.round_half_down = round_half_down  # For the lowest ranked teams, if True, report 0 points; if not, "<0.5"

    def get_ranking(self, explicit_wait=False):
        ranking = []
        page_source = self._get_page_source(self.ranking_url, explicit_wait=explicit_wait)

        if page_source:
            soup = BeautifulSoup(page_source, "html.parser")
            teams = soup.select("div[class*=RankingsTeamItem__Row-]")
            if len(teams) == 0 and not explicit_wait:
                return self.get_ranking(explicit_wait=True)
            rank, points, teamname, players = [], [], [], []
            for team in teams:
                try:  # First pull all numbers; in case of no error, add them all to the running lists
                    try:
                        this_pt = int(team.select('div[class*=Points]')[0].find("span").next.strip())
                    except TypeError:
                        if self.round_half_down:
                            this_pt = 0
                        else:
                            this_pt = team.select('div[class*=Points]')[0].find("span").text.split()[0]
                    this_name = str(team.select('div[class*=TeamName]')[0].select('a[class]')[0].next)
                    this_rank = int(team.select('span[class*=WorldRankBadge__Number]')[0].next)
                    this_players = ([x.text for x in team.select("span[class*=PlayerBadgeHead]")] +
                                    [x.text for x in team.select("span[class*=PlayerBadgeTiny]")])
                    points.append(this_pt)
                    teamname.append(this_name)
                    rank.append(this_rank)
                    players.append(this_players)
                except TypeError as e:
                    print('Not succeeded: ', team, e)
            ranking = [{'position': rank[i], 'name': teamname[i], 'points': points[i], 'players': players[i]}
                       for i in range(len(points))]  # TODO: refactor, but first try to see if it works

        self.close()
        return ranking


class ValveRankings(CSRankings):

    def __init__(self, assume_git=False, keep_repository=False):
        super().__init__()
        self.curr_year = 2024  # TODO: pull this from today but can go wrong on jan 1st when there is no 2025 ranking yet
        self.keep_repository = keep_repository
        self.valve_ranking_folder = 'live'

        if not assume_git:
            print('Checking git version to see if git is installed (can suppress with assume_git=True input)')
            error_code = os.system('git --version')
            if error_code != 0:
                raise SystemError("Git seems to not be installed on your system, which is required for ValveRankings."
                                  "Consider installing Git, or use ValveLiveRankings for the HLTV implementation.")

    def get_ranking(self, region='global', date=None):
        # Parsing inputs
        if date is not None:
            if not (len(date) == 10 and date[4] == date[7] == '_'):
                raise ValueError(f"date input should be of form YYYY_MM_DD, not {date}")
        date = date if date is not None else ""
        if region in ['global', 'europe', 'asia', 'americas']:
            region = region
        else:
            raise ValueError(f"Region input should be one of 'global', 'europe', 'asia', 'americas'; you used {region}.")


        # Clone valve regional standings into tmp/ and find file containing selected rankings
        os.makedirs('tmp/', exist_ok=True)
        os.chdir('tmp/')
        if 'counter-strike_regional_standings' in os.listdir():  # In case you have previously kept the repository
            os.chdir('counter-strike_regional_standings')
            os.system('git pull')
            os.chdir(f'{self.valve_ranking_folder}/{self.curr_year}/')
        else:
            os.system('git clone git@github.com:ValveSoftware/counter-strike_regional_standings.git')
            os.chdir(f'counter-strike_regional_standings/{self.valve_ranking_folder}/{self.curr_year}/')
        allowed_files = sorted([x for x in os.listdir() if region in x and date in x])
        if len(allowed_files) == 0:
            raise FileNotFoundError(f'No files can be found for {region} region and date={date}.')
        most_recent_allowed_file = allowed_files[-1]
        print(f"Importing valve rankings from {most_recent_allowed_file}.")

        # Read in selected rankings
        with open(most_recent_allowed_file, 'r') as f:
            valve_standings_md = f.read().splitlines()

        # Remove cloned repo and (if it's empty) tmp/
        os.chdir('../../../../')
        if not self.keep_repository:
            shutil.rmtree('tmp/counter-strike_regional_standings')
            if len(os.listdir('tmp')) == 0:
                os.removedirs('tmp')

        # Process the standings to something workable, and save it
        rank, points, teamname, players = [], [], [], []
        for row in valve_standings_md[5:-4]:
            row = [x.strip() for x in row.split('|')][1:5]
            rank.append(int(row[0]))
            points.append(int(row[1]))
            teamname.append(row[2])
            players.append(row[3].split(', '))

        ranking = [{'position': rank[i], 'name': teamname[i], 'points': points[i], 'players': players[i]}
                   for i in range(len(points))]  # TODO: refactor, but first try to see if it works

        return ranking


class ValveInvitationRankings(ValveRankings):

    def __init__(self, assume_git=False, keep_repository=False):
        super().__init__(assume_git=assume_git, keep_repository=keep_repository)
        self.valve_ranking_folder = 'invitation'
