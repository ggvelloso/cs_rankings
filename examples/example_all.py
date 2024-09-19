from hltv_data2 import ValveLiveRankings, HLTVRankings, ESLRankings, ValveRankings, ValveInvitationRankings


for ranking in [ValveLiveRankings, HLTVRankings, ESLRankings, ValveRankings, ValveInvitationRankings][3:4]:

    client = ranking()
    ranking = client.get_ranking()
    print(ranking)
