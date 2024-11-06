# CS rankings

> Pull competitive Counterstrike rankings from HLTV.org, ESL and Valve.

This is done using a Selenium-based webview for HLTV.org and ESL, and using a clone of the git repository for the Valve
rankings. Valve rankings can also be pulled from HLTV, see below.

[//]: # (## Install)

[//]: # ()
[//]: # (```sh)

[//]: # (pip install hltv-data)

[//]: # (```)

## Usage

The public methods can be reached by importing from `cs_rankings`.
```python
from cs_rankings import HLTVRankings, ESLRankings, ValveLiveRankings, ValveRankings, ValveInvitationRankings

client = ValveRankings()  # or one of the others
ranking = client.get_ranking()
client.close()
```

The variable `ranking` will be a list of dictionaries for each rank. The dictionaries contain key, value pairs for 
`position`, `name`, `points` and `players`.

You can easily convert them to, say, a pandas DataFrame using `pd.DataFrame(ranking)`.


## Details on the rankings
There are five Rankings classes available, three that are based on Selenium-based webviews and two based on the git
approach. Note that for the git-based rankings you will need to have git installed beforehand.

Selenium-based:
- HLTVRankings
- ValveLiveRankings (the Valve rankings as live calculated by HLTV)
- ESLRankings

Git-based:
- ValveRankings (the official ones on the Valve own git)
- ValveInvitationRankings (the official ones used for invitations)

### Additional options
For the selenium-based rankings, the init call supports two extra arguments:
```python
from cs_rankings import HLTVRankings

client = HLTVRankings(driver=None, in_container=False)
```
The driver input can be used to initialize your own `selenium.webdriver.Chrome()` driver (or in theory a non-Chrome
driver, but that is not tested) with your own settings (such as specific `selenium.webdriver.chrome.options.Options` you
might need). If not supplied, a default set of options will be supplied. If `in_container` is set to True, the default
options are extended to make them work in Docker containers.

For the git-based rankings, the init call supports two extra arguments:
```python
from cs_rankings import ValveRankings

client = ValveRankings(assume_git=True, keep_repository=True)
```
Both are False by default. If `assume_git` is set to True, there will be no check on whether Git is installed. If 
`keep_repository` is set to True, the Valve git repository will not be removed afterwards, which allows for quick reuse.

For all rankings (git-based or selenium-based), the `get_ranking()` method supports four extra arguments:
```python
from cs_rankings import HLTVRankings

client = HLTVRankings()
ranking = client.get_ranking(region='asia', date='2024/september/2', min_points=10, max_rank=30)
```
By default, the most recent global ranking is pulled without filtering by points or maximum rank. Note that supported
regions for the HLTV and Valve rankings are differently formatted.

Note: it is not possible to use the `region` or `date` inputs for the ESLRanking only. The ESLRanking does support the point
or ranking based filter.

## Inspiration & credits
This project is based on the [hltv-data](https://github.com/dchoruzy/hltv-data) project by 
[@dchoruzy](https://github.com/dchoruzy). That project aims to pull rankings, matches and results from the HLTV website.
This project is a fork and rework of `hltv-data`'s main class.

Compared to `hltv-data`, this project is more narrow since it focuses on rankings only, but it is wider since it can 
pull more detailed rankings and from multiple sources.

## Contributing
Contributions, issues and feature requests are welcome!
