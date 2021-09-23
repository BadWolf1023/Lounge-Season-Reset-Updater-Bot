'''
Created on Aug 24, 2021

@author: willg
'''
import common
import Player

async def read_player_data_in(message_sender, to_load, verbose=False, alternative_ctx=None):
    common.all_player_data.clear()
    for player_data in to_load:
        if len(player_data) == 0:
            continue
        
        if len(player_data) > 0:
            try:
                cur_player = Player.Player(player_data)
                lookup_name = cur_player.get_lookup_name()
                if lookup_name in common.all_player_data:
                    await message_sender.queue_message(f"Warning: Duplicate player: {cur_player.name}", is_once_every_24_hr_message=True, alternative_ctx=alternative_ctx)
                else:
                    common.all_player_data[lookup_name] = cur_player
            except Player.BadDataGiven:
                await message_sender.queue_message(f"This data received contains bad data: {player_data}", alternative_ctx=alternative_ctx)
    if verbose:
        await message_sender.queue_message(f"Read in {len(common.all_player_data)} players.\nData source (sheet or API) has a total of {len(to_load)} players.", alternative_ctx=alternative_ctx)