'''
Created on Aug 21, 2021

@author: willg
'''
import discord

import CustomExceptions
import core_data_loader
import common
from typing import List
from datetime import datetime, timedelta

RT_PLAYER_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=rt&all=1"
CT_PLAYER_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=ct&all=1"
RT_MMR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderclass.php?ladder_type=rt"
CT_MMR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderclass.php?ladder_type=ct"
RT_LR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderboundary.php?ladder_type=rt"
CT_LR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderboundary.php?ladder_type=ct"
RT_EVENT_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderevent.php?all&ladder_type=rt"
CT_EVENT_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderevent.php?all&ladder_type=ct"

LAST_PLAYER_DATA_PULL_TIME = None
LAST_CUTOFF_PULL_TIME = None
LAST_EVENT_PULL_TIME = None

PLAYER_PULL_CACHE_TIME = timedelta(minutes=10)
CUTOFF_PULL_CACHE_TIME = timedelta(minutes=2)
EVENT_PULL_CACHE_TIME = timedelta(minutes=10)



def print_key_data_error(key, data):
    print('key:', key, 'value:', data[key], "type:", type(data[key]))

class TierDataLoader:
    tier_json_name = "tier"
    event_date_name = "event_date"
    API_REQUIRED_IN_JSON = [tier_json_name, event_date_name]

    @staticmethod
    def __data_is_corrupt__(data):
        if not isinstance(data, dict) or "results" not in data or not isinstance(data["results"], list):
            return True

        for event_data in data["results"]:
            for key in TierDataLoader.API_REQUIRED_IN_JSON:
                if key not in event_data:
                    print(f'The key "{key}" should have been in the cutoff data: {event_data}')
                    return True

            if not common.is_datetime(event_data[TierDataLoader.event_date_name]):
                print_key_data_error(event_data, TierDataLoader.event_date_name)
                return True
        return False

    @staticmethod
    async def __fix_data__(events: List):
        for event in events:
            event[TierDataLoader.event_date_name] = common.get_datetime(event[TierDataLoader.event_date_name])

    @staticmethod
    async def __update_event_data__(rt_tier_data, ct_tier_data):
        await TierDataLoader.__fix_data__(rt_tier_data)
        await TierDataLoader.__fix_data__(ct_tier_data)

        common.RT_EVENT_DATA.clear()
        common.CT_EVENT_DATA.clear()

        for data_piece in rt_tier_data:
            tier = data_piece[TierDataLoader.tier_json_name]
            event_date = data_piece[TierDataLoader.event_date_name]
            common.RT_EVENT_DATA.append((tier, event_date))
        for data_piece in ct_tier_data:
            tier = data_piece[TierDataLoader.tier_json_name]
            event_date = data_piece[TierDataLoader.event_date_name]
            common.CT_EVENT_DATA.append((tier, event_date))

    @staticmethod
    async def update_event_data(interaction, override_cache=False):
        global LAST_EVENT_PULL_TIME
        if not override_cache:
            # Check cache time
            if LAST_EVENT_PULL_TIME is not None and \
                    LAST_EVENT_PULL_TIME + EVENT_PULL_CACHE_TIME > datetime.now():
                return
        rt_event_data = await common.get_json_data(RT_EVENT_DATA_API_URL)
        ct_event_data = await common.get_json_data(CT_EVENT_DATA_API_URL)

        if TierDataLoader.__data_is_corrupt__(rt_event_data):
            await interaction.followup.send("RT Event Data was corrupt.")
            raise CustomExceptions.EventAPIBadData("RT Event Data was corrupt.")
        if TierDataLoader.__data_is_corrupt__(ct_event_data):
            await interaction.followup.send("CT Event Data was corrupt.")
            raise CustomExceptions.EventAPIBadData("CT Event Data was corrupt.")

        await TierDataLoader.__update_event_data__(rt_event_data["results"], ct_event_data["results"])
        LAST_EVENT_PULL_TIME = datetime.now()

class CutoffDataLoader:
    order_json_name = "ladder_order"
    lr_role_json_name = "ladder_boundary_name"
    mmr_role_json_name = "ladder_class_name"
    lower_lr_cutoff_json_name = "minimum_lr"
    lower_mmr_cutoff_json_name = "minimum_mmr"
    API_REQUIRED_IN_LR_JSON = [order_json_name, lr_role_json_name, lower_lr_cutoff_json_name]
    API_REQUIRED_IN_MMR_JSON = [order_json_name, mmr_role_json_name, lower_mmr_cutoff_json_name]

    
    @staticmethod
    def __lr_cutoff_data_is_corrupt__(data):
        if not isinstance(data, dict) or "results" not in data or not isinstance(data["results"], list):
            return True
        

        for cutoff_piece in data["results"]:
            for key in CutoffDataLoader.API_REQUIRED_IN_LR_JSON:
                if key not in cutoff_piece:
                    print(f'The key "{key}" should have been in the cutoff data: {cutoff_piece}')
                    return True
                
            if not common.isint(cutoff_piece[CutoffDataLoader.order_json_name]):
                print_key_data_error(cutoff_piece, CutoffDataLoader.order_json_name)
                return True
            if not isinstance(cutoff_piece[CutoffDataLoader.lr_role_json_name], str):
                print_key_data_error(cutoff_piece, CutoffDataLoader.lr_role_json_name)
                return True
            if not (common.isint(cutoff_piece[CutoffDataLoader.lower_lr_cutoff_json_name]) or cutoff_piece[CutoffDataLoader.lower_lr_cutoff_json_name] is None):
                print_key_data_error(cutoff_piece, CutoffDataLoader.lower_lr_cutoff_json_name)
                return True
        return False
    
    @staticmethod
    def __mmr_cutoff_data_is_corrupt__(data):
        if not isinstance(data, dict) or "results" not in data or not isinstance(data["results"], list):
            return True
        for cutoff_piece in data["results"]:
            
            for key in CutoffDataLoader.API_REQUIRED_IN_MMR_JSON:
                if key not in cutoff_piece:
                    print(f'The key "{key}" should have been in the cutoff data: {cutoff_piece}')
                    return True
            if not common.isint(cutoff_piece[CutoffDataLoader.order_json_name]):
                print_key_data_error(cutoff_piece, CutoffDataLoader.order_json_name)
                return True
            if not isinstance(cutoff_piece[CutoffDataLoader.mmr_role_json_name], str):
                print_key_data_error(cutoff_piece, CutoffDataLoader.mmr_role_json_name)
                return True
            if not (common.isint(cutoff_piece[CutoffDataLoader.lower_mmr_cutoff_json_name]) or cutoff_piece[CutoffDataLoader.lower_mmr_cutoff_json_name] is None):
                print_key_data_error(cutoff_piece, CutoffDataLoader.lower_mmr_cutoff_json_name)
                return True
        return False
    
    @staticmethod
    async def __fix_cutoff_data__(cutoff_data:List, is_rt):
        for cutoff_data_piece in cutoff_data:
            cutoff_data_piece[CutoffDataLoader.order_json_name] = int(cutoff_data_piece[CutoffDataLoader.order_json_name])
            to_append = "RT " if is_rt else "CT "
            if CutoffDataLoader.lr_role_json_name in cutoff_data_piece:
                cutoff_data_piece[CutoffDataLoader.lr_role_json_name] = to_append + cutoff_data_piece[CutoffDataLoader.lr_role_json_name]
            else:
                cutoff_data_piece[CutoffDataLoader.mmr_role_json_name] = to_append + cutoff_data_piece[CutoffDataLoader.mmr_role_json_name]
                
            if CutoffDataLoader.lower_lr_cutoff_json_name in cutoff_data_piece and cutoff_data_piece[CutoffDataLoader.lower_lr_cutoff_json_name] is not None:
                cutoff_data_piece[CutoffDataLoader.lower_lr_cutoff_json_name] = int(cutoff_data_piece[CutoffDataLoader.lower_lr_cutoff_json_name])
            elif CutoffDataLoader.lower_mmr_cutoff_json_name in cutoff_data_piece and cutoff_data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name] is not None:
                cutoff_data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name] = int(cutoff_data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name])
        cutoff_data.sort(key=lambda data_piece: data_piece[CutoffDataLoader.order_json_name], reverse=True)
                
    
    @staticmethod 
    async def __update_common_cutoffs__(rt_mmr_cutoff_data, ct_mmr_cutoff_data, rt_lr_cutoff_data, ct_lr_cutoff_data, interaction: discord.Interaction):
        await CutoffDataLoader.__fix_cutoff_data__(rt_mmr_cutoff_data, is_rt=True)
        await CutoffDataLoader.__fix_cutoff_data__(ct_mmr_cutoff_data, is_rt=False)
        await CutoffDataLoader.__fix_cutoff_data__(rt_lr_cutoff_data, is_rt=True)
        await CutoffDataLoader.__fix_cutoff_data__(ct_lr_cutoff_data, is_rt=False)

        common.RT_CLASS_ROLE_CUTOFFS.clear()
        common.CT_CLASS_ROLE_CUTOFFS.clear()
        common.RT_RANKING_ROLE_CUTOFFS.clear()
        common.CT_RANKING_ROLE_CUTOFFS.clear()

        # RT Class
        for data_piece in rt_mmr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.mmr_role_json_name]
            lower_cutoff_name = data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name]
            common.RT_CLASS_ROLE_CUTOFFS.append((lower_cutoff_name, role_name))
        
        #CT Class
        for data_piece in ct_mmr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.mmr_role_json_name]
            lower_cutoff_name = data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name]
            common.CT_CLASS_ROLE_CUTOFFS.append((lower_cutoff_name, role_name))

        #RT Ranking
        for data_piece in rt_lr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.lr_role_json_name]
            lower_cutoff_name = data_piece[CutoffDataLoader.lower_lr_cutoff_json_name]
            common.RT_RANKING_ROLE_CUTOFFS.append((lower_cutoff_name, role_name))
        
        #CT Ranking
        temp_ct_rank_role_cutoffs = []
        for data_piece in ct_lr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.lr_role_json_name]
            lower_cutoff_name = data_piece[CutoffDataLoader.lower_lr_cutoff_json_name]
            common.CT_RANKING_ROLE_CUTOFFS.append((lower_cutoff_name, role_name))

    @staticmethod 
    async def update_cutoff_data(interaction, override_cache=False):
        global LAST_CUTOFF_PULL_TIME
        if not override_cache:
            # Check cache time
            if LAST_CUTOFF_PULL_TIME is not None and \
                LAST_CUTOFF_PULL_TIME + CUTOFF_PULL_CACHE_TIME > datetime.now():
                return
        rt_mmr_cutoff_data = await common.get_json_data(RT_MMR_CUTOFF_API_URL)
        ct_mmr_cutoff_data = await common.get_json_data(CT_MMR_CUTOFF_API_URL)
        rt_lr_cutoff_data = await common.get_json_data(RT_LR_CUTOFF_API_URL)
        ct_lr_cutoff_data = await common.get_json_data(CT_LR_CUTOFF_API_URL)
        
        if CutoffDataLoader.__mmr_cutoff_data_is_corrupt__(rt_mmr_cutoff_data):
            await interaction.followup.send("RT MMR Cutoff Data was corrupt.")
            raise CustomExceptions.CutoffAPIBadData("RT MMR Cutoff Data was corrupt.")
        if CutoffDataLoader.__mmr_cutoff_data_is_corrupt__(ct_mmr_cutoff_data):
            await interaction.followup.send("CT MMR Cutoff Data was corrupt.")
            raise CustomExceptions.CutoffAPIBadData("CT MMR Cutoff Data was corrupt.")
        if CutoffDataLoader.__lr_cutoff_data_is_corrupt__(rt_lr_cutoff_data):
            await interaction.followup.send("RT LR Cutoff Data was corrupt.")
            raise CustomExceptions.CutoffAPIBadData("RT LR Cutoff Data was corrupt.")
        if CutoffDataLoader.__lr_cutoff_data_is_corrupt__(ct_lr_cutoff_data):
            await interaction.followup.send("CT LR Cutoff Data was corrupt.")
            raise CustomExceptions.CutoffAPIBadData("CT LR Cutoff Data was corrupt.")
        
        await CutoffDataLoader.__update_common_cutoffs__(rt_mmr_cutoff_data["results"], ct_mmr_cutoff_data["results"], rt_lr_cutoff_data["results"], ct_lr_cutoff_data["results"], interaction)
        LAST_CUTOFF_PULL_TIME = datetime.now()


class PlayerDataLoader:
    player_id_json_name = "player_id"
    player_name_json_name = "player_name"
    player_current_mmr_json_name = "current_mmr"
    player_current_lr_json_name = "current_lr"
    player_last_event_date_json_name = "last_event_date"
    player_events_played_json_name = "total_events"
    discord_id_json_name = "discord_user_id"
    API_REQUIRED_IN_JSON = [player_id_json_name, player_name_json_name, player_current_mmr_json_name, player_current_lr_json_name, player_last_event_date_json_name, player_events_played_json_name, discord_id_json_name]
    
    @staticmethod
    def player_data_is_corrupt(data):
        if not isinstance(data, dict) or "results" not in data or not isinstance(data["results"], list):
            return True
    
        for player_data in data["results"]:
            
            for key in PlayerDataLoader.API_REQUIRED_IN_JSON:
                if key not in player_data:
                    print(f'The key "{key}" should have been in the player data: {player_data}')
                    return True
                
            if not common.isint(player_data[PlayerDataLoader.player_id_json_name]):
                print_key_data_error(PlayerDataLoader.player_id_json_name, player_data)
                return True
            if not isinstance(player_data[PlayerDataLoader.player_name_json_name], str):
                print_key_data_error(PlayerDataLoader.player_name_json_name, player_data)
                return True
            if not common.isint(player_data[PlayerDataLoader.player_current_mmr_json_name]):
                print_key_data_error(PlayerDataLoader.player_current_mmr_json_name, player_data)
                return True
            if not common.isint(player_data[PlayerDataLoader.player_current_lr_json_name]):
                print_key_data_error(PlayerDataLoader.player_current_lr_json_name, player_data)
                return True
            if not isinstance(player_data[PlayerDataLoader.player_last_event_date_json_name], str):
                print_key_data_error(PlayerDataLoader.player_last_event_date_json_name, player_data)
                return True
            if not common.isint(player_data[PlayerDataLoader.player_events_played_json_name]):
                print_key_data_error(PlayerDataLoader.player_events_played_json_name, player_data)
                return True
        return False
    
    @staticmethod 
    async def merge_data(rt_data, ct_data):
        results = {}
        for player in rt_data:
            player_id = player[PlayerDataLoader.player_id_json_name]
            if player_id not in results:
                results[player_id] = [None, None, None, None, None, None, None, None, None, None]
                
            results[player_id][0] = player[PlayerDataLoader.player_name_json_name]
            if results[player_id][1] is None:
                results[player_id][1] = player[PlayerDataLoader.discord_id_json_name]
            results[player_id][2] = player[PlayerDataLoader.player_current_mmr_json_name]
            results[player_id][4] = player[PlayerDataLoader.player_current_lr_json_name]
            results[player_id][6] = datetime.min
            results[player_id][8] = player[PlayerDataLoader.player_events_played_json_name]
            if results[player_id][8] != "0":
                try:
                    last_rt_event = player[PlayerDataLoader.player_last_event_date_json_name]
                    if isinstance(last_rt_event, str):
                        results[player_id][6] = datetime.strptime(last_rt_event, '%Y-%m-%d %H:%M:%S')
                except:
                    print(last_rt_event)
        
        for player in ct_data:
            player_id = player[PlayerDataLoader.player_id_json_name]
            if player_id not in results:
                results[player_id] = [None, None, None, None, None, None, None, None, None, None]
                
            results[player_id][0] = player[PlayerDataLoader.player_name_json_name]
            if results[player_id][1] is None:
                results[player_id][1] = player[PlayerDataLoader.discord_id_json_name]
            results[player_id][3] = player[PlayerDataLoader.player_current_mmr_json_name]
            results[player_id][5] = player[PlayerDataLoader.player_current_lr_json_name]
            results[player_id][7] = datetime.min
            results[player_id][9] = player[PlayerDataLoader.player_events_played_json_name]
            if results[player_id][9] != "0":
                try:
                    last_ct_event = player[PlayerDataLoader.player_last_event_date_json_name]
                    if isinstance(last_ct_event, str):
                        results[player_id][7] = datetime.strptime(last_ct_event, '%Y-%m-%d %H:%M:%S')
                except:
                    print(last_ct_event)
            
        return list(results.values())

    @staticmethod 
    async def get_player_data(interaction: discord.Interaction):
        rt_data = await common.get_json_data(RT_PLAYER_DATA_API_URL)
        ct_data = await common.get_json_data(CT_PLAYER_DATA_API_URL)
        
        if PlayerDataLoader.player_data_is_corrupt(rt_data):
            await interaction.followup.send("RT Data was corrupt.")
            raise CustomExceptions.PlayerDataAPIBadData("RT Data was corrupt.")
        if PlayerDataLoader.player_data_is_corrupt(ct_data):
            await interaction.followup.send("CT Data was corrupt.")
            raise CustomExceptions.PlayerDataAPIBadData("CT Data was corrupt.")

        return await PlayerDataLoader.merge_data(rt_data["results"], ct_data["results"])
        
    @staticmethod
    async def update_player_data(interaction: discord.Interaction, override_cache=False):
        global LAST_PLAYER_DATA_PULL_TIME
        if not override_cache:
            # Check cache time
            if LAST_PLAYER_DATA_PULL_TIME is not None and \
                LAST_PLAYER_DATA_PULL_TIME + PLAYER_PULL_CACHE_TIME > datetime.now():
                return

        to_load = await PlayerDataLoader.get_player_data(interaction)
        await core_data_loader.read_player_data_in(interaction, to_load)
        LAST_PLAYER_DATA_PULL_TIME = datetime.now()
    