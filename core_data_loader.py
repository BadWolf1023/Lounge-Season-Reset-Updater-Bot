'''
Created on Aug 24, 2021

@author: willg
'''
import common
import Player


async def read_player_data_in(interaction, to_load):
    common.all_player_data.clear()
    for player_data in to_load:
        if len(player_data) == 0:
            continue

        if len(player_data) > 0:
            try:
                cur_player = Player.Player(player_data)
                lookup_name = cur_player.get_lookup_name()
                if lookup_name in common.all_player_data:
                    await interaction.followup.send(f"Warning: Duplicate player: {cur_player.name}")
                else:
                    common.all_player_data[lookup_name] = cur_player
            except Player.BadDataGiven:
                await interaction.followup.send(f"This data received contains bad data: {player_data}")
