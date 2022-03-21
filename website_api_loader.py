'''
Created on Aug 21, 2021

@author: willg
'''
import CustomExceptions
import core_data_loader
import common
from typing import List
from datetime import datetime
RT_PLAYER_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=rt&all=1"
CT_PLAYER_DATA_API_URL = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=ct&all=1"
RT_MMR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderclass.php?ladder_type=rt"
CT_MMR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderclass.php?ladder_type=ct"
RT_LR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderboundary.php?ladder_type=rt"
CT_LR_CUTOFF_API_URL = "https://www.mkwlounge.gg/api/ladderboundary.php?ladder_type=ct"



def print_key_data_error(key, data):
    print('key:', key, 'value:', data[key], "type:", type(data[key]))

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
    async def __update_common_cutoffs__(rt_mmr_cutoff_data, ct_mmr_cutoff_data, rt_lr_cutoff_data, ct_lr_cutoff_data, message_sender, verbose=False, alternative_ctx=None):
        await CutoffDataLoader.__fix_cutoff_data__(rt_mmr_cutoff_data, is_rt=True)
        await CutoffDataLoader.__fix_cutoff_data__(ct_mmr_cutoff_data, is_rt=False)
        await CutoffDataLoader.__fix_cutoff_data__(rt_lr_cutoff_data, is_rt=True)
        await CutoffDataLoader.__fix_cutoff_data__(ct_lr_cutoff_data, is_rt=False)
        
        all_roles = message_sender.running_channel.guild.roles
        
        #RT Class role finding and loading
        temp_rt_class_role_cutoffs = []
        for data_piece in rt_mmr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.mmr_role_json_name]
            fixed_role_name = role_name.lower().replace(" ", "")
            role_id = None
            for role in all_roles:
                if role.name.lower().replace(" ", "") == fixed_role_name:
                    role_id = role.id
                    break
            else:
                error_message = f"No role found in the server named {role_name}"
                await message_sender.queue_message(error_message, True, alternative_ctx=alternative_ctx)
                raise CustomExceptions.NoRoleFound(error_message)
            temp_rt_class_role_cutoffs.append((data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name], role_name, role_id))
        
        #CT Class role finding and loading
        temp_ct_class_role_cutoffs = []
        for data_piece in ct_mmr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.mmr_role_json_name]
            fixed_role_name = role_name.lower().replace(" ", "")
            role_id = None
            for role in all_roles:
                if role.name.lower().replace(" ", "") == fixed_role_name:
                    role_id = role.id
                    break
            else:
                error_message = f"No role found in the server named {role_name}"
                await message_sender.queue_message(error_message, True, alternative_ctx=alternative_ctx)
                raise CustomExceptions.NoRoleFound(error_message)
            temp_ct_class_role_cutoffs.append((data_piece[CutoffDataLoader.lower_mmr_cutoff_json_name], role_name, role_id))
            
            
        #RT Ranking role finding and loading
        temp_rt_rank_role_cutoffs = []
        for data_piece in rt_lr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.lr_role_json_name]
            fixed_role_name = role_name.lower().replace(" ", "")
            role_id = None
            for role in all_roles:
                if role.name.lower().replace(" ", "") == fixed_role_name:
                    role_id = role.id
                    break
            else:
                error_message = f"No role found in the server named {role_name}"
                await message_sender.queue_message(error_message, True, alternative_ctx=alternative_ctx)
                raise CustomExceptions.NoRoleFound(error_message)
            temp_rt_rank_role_cutoffs.append((data_piece[CutoffDataLoader.lower_lr_cutoff_json_name], role_name, role_id))
        
        #CT Ranking role finding and loading
        temp_ct_rank_role_cutoffs = []
        for data_piece in ct_lr_cutoff_data:
            role_name = data_piece[CutoffDataLoader.lr_role_json_name]
            fixed_role_name = role_name.lower().replace(" ", "")
            role_id = None
            for role in all_roles:
                if role.name.lower().replace(" ", "") == fixed_role_name:
                    role_id = role.id
                    break
            else:
                error_message = f"No role found in the server named {role_name}"
                await message_sender.queue_message(error_message, True, alternative_ctx=alternative_ctx)
                raise CustomExceptions.NoRoleFound(error_message)
            temp_ct_rank_role_cutoffs.append((data_piece[CutoffDataLoader.lower_lr_cutoff_json_name], role_name, role_id))
            

        common.RT_CLASS_ROLE_CUTOFFS.clear()
        common.RT_CLASS_ROLE_CUTOFFS.extend(temp_rt_class_role_cutoffs)
        common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE.clear()
        common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE.update({data[2] for data in common.RT_CLASS_ROLE_CUTOFFS})
        

        common.CT_CLASS_ROLE_CUTOFFS.clear()
        common.CT_CLASS_ROLE_CUTOFFS.extend(temp_ct_class_role_cutoffs)
        common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE.clear()
        common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE.update({data[2] for data in common.CT_CLASS_ROLE_CUTOFFS})
        

        common.RT_RANKING_ROLE_CUTOFFS.clear()
        common.RT_RANKING_ROLE_CUTOFFS.extend(temp_rt_rank_role_cutoffs)
        common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE.clear()
        common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE.update({data[2] for data in common.RT_RANKING_ROLE_CUTOFFS})

        common.CT_RANKING_ROLE_CUTOFFS.clear()
        common.CT_RANKING_ROLE_CUTOFFS.extend(temp_ct_rank_role_cutoffs)
        common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE.clear()
        common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE.update({data[2] for data in common.CT_RANKING_ROLE_CUTOFFS})
                
    
    
    @staticmethod 
    async def update_cutoff_data(message_sender, verbose=False, alternative_ctx=None):
        rt_mmr_cutoff_data = await common.getJSONData(RT_MMR_CUTOFF_API_URL)
        ct_mmr_cutoff_data = await common.getJSONData(CT_MMR_CUTOFF_API_URL)
        rt_lr_cutoff_data = await common.getJSONData(RT_LR_CUTOFF_API_URL)
        ct_lr_cutoff_data = await common.getJSONData(CT_LR_CUTOFF_API_URL)
        
        if CutoffDataLoader.__mmr_cutoff_data_is_corrupt__(rt_mmr_cutoff_data):
            await message_sender.queue_message("RT MMR Cutoff Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.CutoffAPIBadData("RT MMR Cutoff Data was corrupt.")
        if CutoffDataLoader.__mmr_cutoff_data_is_corrupt__(ct_mmr_cutoff_data):
            await message_sender.queue_message("CT MMR Cutoff Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.CutoffAPIBadData("CT MMR Cutoff Data was corrupt.")
        if CutoffDataLoader.__lr_cutoff_data_is_corrupt__(rt_lr_cutoff_data):
            await message_sender.queue_message("RT LR Cutoff Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.CutoffAPIBadData("RT LR Cutoff Data was corrupt.")
        if CutoffDataLoader.__lr_cutoff_data_is_corrupt__(ct_lr_cutoff_data):
            await message_sender.queue_message("CT LR Cutoff Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.CutoffAPIBadData("CT LR Cutoff Data was corrupt.")
        
        return await CutoffDataLoader.__update_common_cutoffs__(rt_mmr_cutoff_data["results"], ct_mmr_cutoff_data["results"], rt_lr_cutoff_data["results"], ct_lr_cutoff_data["results"], message_sender, verbose, alternative_ctx)



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
    async def get_player_data(message_sender, verbose=False, alternative_ctx=None):
        rt_data = await common.getJSONData(RT_PLAYER_DATA_API_URL)
        ct_data = await common.getJSONData(CT_PLAYER_DATA_API_URL)
        
        if PlayerDataLoader.player_data_is_corrupt(rt_data):
            await message_sender.queue_message("RT Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.PlayerDataAPIBadData("RT Data was corrupt.")
        if PlayerDataLoader.player_data_is_corrupt(ct_data):
            await message_sender.queue_message("CT Data was corrupt.", True, alternative_ctx=alternative_ctx)
            raise CustomExceptions.PlayerDataAPIBadData("CT Data was corrupt.")
        
        return await PlayerDataLoader.merge_data(rt_data["results"], ct_data["results"])
        
    @staticmethod
    async def update_player_data(message_sender, verbose=False, alternative_ctx=None):
        to_load = await PlayerDataLoader.get_player_data(message_sender, verbose, alternative_ctx)
        await core_data_loader.read_player_data_in(message_sender, to_load, verbose, alternative_ctx)
    