import abc
import os
import shutil
import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


month_mapping = {'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11',
                 'december': '12'}
rev_month_mapping = {v: k for k,v in month_mapping.items()}


class CSRankings(abc.ABC):

    @abc.abstractmethod
    def get_ranking(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    def _convert_date(self, date, style=None):
        # Convert input dates to needed date format for Valve or HLTV pulls (ESL does not allow old rankings by URL)
        # You can plug in either format or YYYYMMDD / YYYY-MM-DD formats for compatibility, or a datetime date(time).
        if type(date) == datetime.datetime:
            date = str(date.date())
        elif type(date) == datetime.date:
            date = str(date)

        if len(date) == 10 and date.count('_') == 2:
            year, month, day = date.split('_')
        elif len(date) == 10 and date.count('-') == 2:
            year, month, day = date.split('-')
        elif len(date) == 8 and not any(x in date for x in '-/_'):
            year, month, day = date[:4], date[4:6], date[6:]
        elif date.count('/') == 2:
            year, day = date.split('/')[0], date.split('/')[2].zfill(2)
            month = month_mapping[date.split('/')[1]]
        else:
            raise ValueError(f'Date input {date} does not meet standards: YYYYMMDD or YYYY_MM_DD or YYYY-MM-DD or '
                             f'YYYY/month/D.')
        try:
            assert len(year) == 4
            assert len(month) == 2
            assert len(day) == 2
        except AssertionError:
            raise ValueError(f'Date input {date} does not meet standards: YYYYMMDD or YYYY_MM_DD or YYYY-MM-DD or '
                             f'YYYY/month/D.')

        # Output style formatting: HLTV, Valve, or generic datetime-like
        if style is None:
            if isinstance(self, HLTVRankings):
                style = 'hltv'
            if isinstance(self, ValveRankings):
                style = 'valve'
        if style == 'hltv':
            return year + '/' + rev_month_mapping[month] + '/' + str(int(day))
        if style == 'valve':
            return year + '_' + month + '_' + day
        else:
            return year + '-' + month + '-' + day


class CSRankingsClient(CSRankings, abc.ABC):
    def __init__(self, driver=None, in_container=False):
        if driver is None:
            options = self._get_default_options() if not in_container else self._get_container_options()
            self.driver = webdriver.Chrome(options=options)
        else:
            self.driver=driver
        self.ranking_url = ""

    @staticmethod
    def _get_default_options():
        options = Options()
        options.add_argument("--disable-search-engine-choice-screen")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/79.0.3945.130 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--headless=new")
        return options

    def _get_container_options(self):
        options = self._get_default_options()
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
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

    def __init__(self, driver=None, in_container=False):
        super().__init__(driver=driver, in_container=in_container)
        BASE_URL = "https://www.hltv.org"
        self.ranking_url = f"{BASE_URL}/ranking/teams/"
        self.region_string = 'country'

    def get_ranking(self, date=None, region=None, min_points=0, max_rank=None):
        # Process date/region input - for now assume user will supply an allowed region
        date = self._convert_date(date, style='hltv') if date is not None else ''
        this_ranking_url = self.ranking_url + date
        region = None if region in ['global', None] else region.capitalize()
        this_ranking_url += f'/{self.region_string}/{region}' if region is not None else ''
        print(this_ranking_url)

        ranking = []
        page_source = self._get_page_source(this_ranking_url)
        if page_source:
            soup = BeautifulSoup(page_source, "html.parser")
            teams = soup.find_all("div", {"class": "ranked-team"})
            for team in teams[:max_rank]:
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
                if int(points) < min_points:
                    break  # No future teams would have more points, so can break the for-loop
                ranking_item = {
                    "position": int(position),
                    "name": name,
                    "points": int(points),
                    "players": players
                }
                ranking.append(ranking_item)

        return ranking


class ValveLiveRankings(HLTVRankings):

    def __init__(self, driver=None, in_container=False):
        super().__init__(driver=driver, in_container=in_container)
        BASE_URL = "https://www.hltv.org"
        self.ranking_url = f"{BASE_URL}/valve-ranking/teams/"
        self.region_string = 'region'


class ESLRankings(CSRankingsClient):

    def __init__(self, driver=None, round_half_down=True, in_container=False):
        super().__init__(driver=driver, in_container=in_container)
        self.ranking_url = "https://pro.eslgaming.com/worldranking/csgo/rankings/"
        self.round_half_down = round_half_down  # For the lowest ranked teams, if True, report 0 points; if not, "<0.5"

    def get_ranking(self, explicit_wait=False, min_points=0, max_rank=None):
        ranking = []
        page_source = self._get_page_source(self.ranking_url, explicit_wait=explicit_wait)

        if page_source:
            soup = BeautifulSoup(page_source, "html.parser")
            teams = soup.select("div[class*=RankingsTeamItem__Row-]")
            if len(teams) == 0 and not explicit_wait:
                return self.get_ranking(explicit_wait=True, min_points=min_points, max_rank=max_rank)
            rank, points, teamname, players = [], [], [], []
            for team in teams[:max_rank]:
                try:  # First pull all numbers; in case of no error, add them all to the running lists
                    try:
                        this_pt = int(team.select('div[class*=Points]')[0].find("span").next.strip())
                    except TypeError:
                        if self.round_half_down:
                            this_pt = 0
                        else:
                            this_pt = team.select('div[class*=Points]')[0].find("span").text.split()[0]
                    if this_pt < min_points:
                        break
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

        return ranking


class ValveRankings(CSRankings):
    valve_ranking_folder = 'live'

    def __init__(self, assume_git=False, keep_repository=False):
        super().__init__()
        self.curr_year = 2024  # TODO: pull this from today but can go wrong on jan 1st when there is no 2025 ranking yet
        self.keep_repository = keep_repository

        if not assume_git:
            print('Checking git version to see if git is installed (can suppress with assume_git=True input)')
            error_code = os.system('git --version')
            if error_code != 0:
                raise SystemError("Git seems to not be installed on your system, which is required for ValveRankings."
                                  "Consider installing Git, or use ValveLiveRankings for the HLTV implementation.")

        # Clone valve regional standings into tmp/ and find file containing selected rankings
        os.makedirs('tmp/', exist_ok=True)
        os.chdir('tmp/')
        if 'counter-strike_regional_standings' in os.listdir():  # In case you have previously kept the repository
            os.chdir('counter-strike_regional_standings')
            os.system('git pull')
            os.chdir(f'{self.valve_ranking_folder}/{self.curr_year}/')
        else:
            os.system('git clone https://github.com/ValveSoftware/counter-strike_regional_standings.git')
            os.chdir(f'counter-strike_regional_standings/{self.valve_ranking_folder}/{self.curr_year}/')

    def get_ranking(self, region='global', date=None, min_points=0, max_rank=None):
        # Parsing inputs
        date = self._convert_date(date, style='valve') if date is not None else ''
        if region in ['global', 'europe', 'asia', 'americas']:
            region = region
        else:
            raise ValueError(f"Region input should be one of 'global', 'europe', 'asia', 'americas'; you used {region}.")

        allowed_files = sorted([x for x in os.listdir() if region in x and date in x])
        if len(allowed_files) == 0:
            raise FileNotFoundError(f'No files can be found for {region} region and date={date}.')
        most_recent_allowed_file = allowed_files[-1]
        print(f"Importing valve rankings from {most_recent_allowed_file}.")

        # Read in selected rankings
        with open(most_recent_allowed_file, 'r') as f:
            valve_standings_md = f.read().splitlines()

        # Process the standings to something workable, and save it
        rank, points, teamname, players = [], [], [], []
        for row in valve_standings_md[5:-4][:max_rank]:
            row = [x.strip() for x in row.split('|')][1:5]
            if int(row[1]) < min_points:
                break
            rank.append(int(row[0]))
            points.append(int(row[1]))
            teamname.append(row[2])
            players.append(row[3].split(', '))

        ranking = [{'position': rank[i], 'name': teamname[i], 'points': points[i], 'players': players[i]}
                   for i in range(len(points))]  # TODO: refactor, but first try to see if it works

        return ranking

    def close(self):
        os.chdir('../../../../')
        # Remove cloned repo and (if it's empty) tmp/
        if not self.keep_repository:
            shutil.rmtree('tmp/counter-strike_regional_standings')
            if len(os.listdir('tmp')) == 0:
                os.removedirs('tmp')


class ValveInvitationRankings(ValveRankings):
    valve_ranking_folder = 'invitation'

    def __init__(self, assume_git=False, keep_repository=False):
        super().__init__(assume_git=assume_git, keep_repository=keep_repository)
