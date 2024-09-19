from cs_rankings import ValveLiveRankings, HLTVRankings, ESLRankings, ValveRankings, ValveInvitationRankings

# Important note: don't run this more than needed to avoid unneeded traffic on the websites.

# Pull current rankings from ESL
esl_client = ESLRankings()
print("\nESL rankings from today")
print(esl_client.get_ranking())
esl_client.close()


# Pull the Valve rankings used for invites for each region, and keep the repository
valve_client = ValveInvitationRankings(assume_git=True, keep_repository=True)
print("\nMost recent Valve invitation rankings by region")
[print(valve_client.get_ranking(region=x)) for x in ['asia', 'americas', 'europe']]
valve_client.close()


# Pull the most recent official Valve rankings, and then delete the repository
valve_client = ValveRankings(assume_git=True, keep_repository=True)
print("\nMost recent official Valve ranking")
print(valve_client.get_ranking())
valve_client.close()


# Pull Valve rankings as calculated live by HLTV, from two different dates using 2 different ways
valve_hltv_client = ValveLiveRankings()
print("\nValve ranking as calculated by HLTV for 2024-09-01 and 2024-09-02")
print(valve_hltv_client.get_ranking(date='2024-09-01'))
valve_hltv_client.close()

valve_hltv_client = ValveLiveRankings()  # Need to close and restart due to bot detection
print(valve_hltv_client.get_ranking(date='20240902'))
valve_hltv_client.close()


# Pull HLTV rankings, from now and from September 2 in two different ways
hltv_client = HLTVRankings()
print("\nHLTV most recent ranking")
print(hltv_client.get_ranking())
hltv_client.close()

print("\nHLTV ranking for 2024-09-02 specified in 2 ways")
hltv_client = HLTVRankings()
print(hltv_client.get_ranking(date='2024/september/2'))
hltv_client.close()
hltv_client = HLTVRankings()
print(hltv_client.get_ranking(date='2024_09_02'))
hltv_client.close()
