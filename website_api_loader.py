'''
Created on Aug 21, 2021

@author: willg
'''
import requests
rt_specific_url = "https://mariokartboards.com/lounge/api/ladderplayer.php?ladder_id=1&all=1"
ct_specific_url = "https://mariokartboards.com/lounge/api/ladderplayer.php?ladder_id=2&all=1"
player_id_json_name = "player_id"
player_name_json_name = "player_name"
player_current_mmr_json_name = "current_mmr"
player_current_lr_json_name = "current_lr"
from common import *
class BadAPIData(Exception):
    pass

#============== Synchronous HTTPS Functions ==============
def fetch(url, headers=None):
    response = requests.get(url)
    return response.json()


        
def data_is_corrupt(data):
    if not isinstance(data, dict) or "results" not in data or not isinstance(data["results"], list):
        return True

    for player_data in data["results"]:
        if player_id_json_name in player_data and isinstance(player_data[player_id_json_name], str) and isint(player_data[player_id_json_name])\
        and player_name_json_name in player_data and isinstance(player_data[player_name_json_name], str) \
        and player_current_mmr_json_name in player_data and isinstance(player_data[player_current_mmr_json_name], str) and isint(player_data[player_current_mmr_json_name])\
        and player_current_lr_json_name in player_data and isinstance(player_data[player_current_lr_json_name], str) and isint(player_data[player_current_lr_json_name]):
            continue
        print(player_data)
        return True
    return False
        
def merge_data(rt_data, ct_data):
    results = {}
    for player in rt_data:
        player_id = player[player_id_json_name]
        if player_id not in results:
            results[player_id] = [None, None, None, None, None, None]
            
        results[player_id][0] = player[player_name_json_name]
        results[player_id][1] = None
        results[player_id][2] = player[player_current_mmr_json_name]
        results[player_id][4] = player[player_current_lr_json_name]
    
    for player in ct_data:
        player_id = player[player_id_json_name]
        if player_id not in results:
            results[player_id] = [None, None, None, None, None, None]
            
        results[player_id][0] = player[player_name_json_name]
        results[player_id][1] = None
        results[player_id][3] = player[player_current_mmr_json_name]
        results[player_id][5] = player[player_current_lr_json_name]
        
    return list(results.values())
    
def get_player_data():
    rt_data = fetch(rt_specific_url)
    ct_data = fetch(ct_specific_url)
    
    if data_is_corrupt(rt_data):
        raise BadAPIData("RT Data was corrupt.")
    if data_is_corrupt(ct_data):
        raise BadAPIData("CT Data was corrupt.")
    
    return merge_data(rt_data["results"], ct_data["results"])
    
    