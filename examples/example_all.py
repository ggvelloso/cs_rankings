from hltv_data2 import ValveLiveRankings, HLTVRankings, ESLRankings


for ranking in [ValveLiveRankings, HLTVRankings, ESLRankings][2:]:

    client = ranking()
    ranking = client.get_ranking()
    print(ranking)
