'''
Created on Aug 21, 2021

@author: willg
'''

import aiohttp
from typing import List, Tuple
import os
from pathlib import Path
import discord
from datetime import datetime

TESTING = True
TESTING_SERVER_ID = 1112604633454628864
MKW_LOUNGE_GUILD_ID = 387347467332485122
BAD_WOLF_ID = 1110408991839883274
DISCORD_MAX_MESSAGE_LEN = 2000

# Currently, for S7, this number is the current season's LR
RT_RANKING_ROLE_CUTOFFS = []
CT_RANKING_ROLE_CUTOFFS = []

# Currently, for S7, this number is the previous season's MMR
RT_CLASS_ROLE_CUTOFFS = []
CT_CLASS_ROLE_CUTOFFS = []

# Holds event data: tier and date/time of event
RT_EVENT_DATA = []
CT_EVENT_DATA = []

test_cutoffs = []

all_player_data = {}


async def safe_send_missing_permissions(interaction: discord.Interaction):
    try:
        await interaction.followup.send("I'm missing permissions. Contact your admins. The bot needs the following permissions:\n- Send Messages\n- Attach files")
    except discord.errors.Forbidden:  # We can't send messages
        pass


async def safe_send_file(interaction: discord.Interaction, content):
    file_name = str(interaction.id) + ".txt"
    Path('./attachments').mkdir(parents=True, exist_ok=True)
    file_path = "./attachments/" + file_name
    with open(file_path, "w") as f:
        f.write(content)

    txt_file = discord.File(file_path, filename=file_name)
    try:
        await interaction.followup.send(file=txt_file)
    except discord.errors.Forbidden:
        await safe_send_missing_permissions(interaction)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# Assumes cutoff data is already sorted
def cutoff_display_text(cutoff_data: List[Tuple[int, str, int]]):
    to_return = []

    last_mmr = None
    for index, (min_mmr, class_name) in enumerate(cutoff_data):
        if index == 0:
            to_return.append(f"{class_name} —> {'-Infinity' if min_mmr is None else min_mmr}+ MMR")
        else:
            if min_mmr is None:
                to_return.append(f"{class_name} —> <{last_mmr} MMR")
            else:
                to_return.append(f"{class_name} —> {min_mmr} - {last_mmr - 1} MMR")
        last_mmr = min_mmr
    return "\n".join(reversed(to_return))


def is_lounge(interaction: discord.Interaction):
    return interaction.guild_id == TESTING_SERVER_ID or interaction.guild_id == MKW_LOUNGE_GUILD_ID


async def get_json_data(full_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(full_url) as r:
            if r.status == 200:
                js = await r.json()
                return js


def isfloat(value: str):
    try:
        float(value)
        return True
    except ValueError:
        return False


def isint(value: str):
    try:
        int(value)
        return True
    except:
        return False

def is_datetime(value: str):
    """Example from 255MP API: 2023-07-22 07:01:13"""
    try:
        datetime_object = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return True
    except:
        return False

def get_datetime(value: str):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

def get_member_info(member):
    return f"{member.mention} ({member.display_name} - {str(member)})"
