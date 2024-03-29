'''
Created on Aug 21, 2021

@author: willg
'''

import aiohttp
from typing import List, Tuple
import os
from pathlib import Path
import discord


TESTING_SERVER_ID = 739733336871665696
BAD_WOLF_ID = 706120725882470460
TESTING=True
MKW_LOUNGE_GUILD_ID = 387347467332485122
DISCORD_MAX_MESSAGE_LEN = 2000
SERVER_ID_TO_IMPERSONATE = None

mkw_lounge_staff_roles = set([387347888935534593, #Boss
                              792805904047276032, #CT Admin
                              399382503825211393, #HT RT Arb
                              399384750923579392, #LT RT Arb
                              521149807994208295, #HT CT Arb
                              792891432301625364 #LT CT Arb
                              ])





#These are the cutoffs. If a player has less than or equal to the first number tuple, they will receive this role
#Currently, for S7, this number is the current season's LR
RT_RANKING_ROLE_CUTOFFS = []

CT_RANKING_ROLE_CUTOFFS = []


#These are the cutoffs. If a player has less than or equal to the first number tuple
#Currently, for S7, this number is the previous season's MMR
RT_CLASS_ROLE_CUTOFFS = []

CT_CLASS_ROLE_CUTOFFS = []

test_cutoffs = []

#For players to get an updated RT Ranking role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = set()
#For players to get an updated CT Ranking role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = set()
#For players to get an updated RT Class role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = set()
#For players to get an updated CT Class role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = set()

all_player_data = {}

REGULAR_TRACKS_ROLE_ID = 520829050030129182
CUSTOM_TRACKS_ROLE_ID = 520828983630364689
ALL_TRACKS_ROLE_ID = 520829099841814539
UNVERIFIED_ROLE_ID = 520821431899258890
WAITING_ROOM_RT_ROLES = {REGULAR_TRACKS_ROLE_ID}
WAITING_ROOM_CT_ROLES = {CUSTOM_TRACKS_ROLE_ID}
WAITING_ROOM_RT_CT_ROLES = {ALL_TRACKS_ROLE_ID, UNVERIFIED_ROLE_ID}
WAIT_ROOM_ROLE_IDS = WAITING_ROOM_RT_ROLES | WAITING_ROOM_CT_ROLES | WAITING_ROOM_RT_CT_ROLES

RT_ROLE_REQUEST_ID = 555914639205204018
CT_ROLE_REQUEST_ID = 520971584182419491

RT_PLACEMENT_ROLE_ID = 723753340063842345
CT_PLACEMENT_ROLE_ID = 723753312331104317
PLACEMENT_ROLE_IDS = {RT_PLACEMENT_ROLE_ID, CT_PLACEMENT_ROLE_ID}


#List will contain 2 items, rt role id in first index, ct role id in 2nd index
top_role_ids = []

    
async def safe_send_missing_permissions(ctx, delete_after=None):
    try:
        await ctx.reply("I'm missing permissions. Contact your admins. The bot needs the following permissions:\n- Send Messages\n- Attach files", delete_after=delete_after)
    except discord.errors.Forbidden: #We can't send messages
        pass
    
async def safe_send_file(ctx, content):
    file_name = str(ctx.message.id) + ".txt"
    Path('./attachments').mkdir(parents=True, exist_ok=True)
    file_path = "./attachments/" + file_name
    with open(file_path, "w") as f:
        f.write(content)
        
    txt_file = discord.File(file_path, filename=file_name)
    try:
        await ctx.reply(file=txt_file)
    except discord.errors.Forbidden:
        safe_send_missing_permissions(ctx)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            
#Assumes cutoff data is already sorted
def cutoff_display_text(cutoff_data:List[Tuple[int, str, int]]):
    to_return = []
    
    last_mmr = None
    for index, (min_mmr, class_name, _) in enumerate(cutoff_data):
        if index == 0:
            to_return.append(f"{class_name} —> {'-Infinity' if min_mmr is None else min_mmr}+ MMR")
        else:
            if min_mmr is None:
                to_return.append(f"{class_name} —> <{last_mmr} MMR")
            else:
                to_return.append(f"{class_name} —> {min_mmr} - {last_mmr-1} MMR")
        last_mmr = min_mmr
    return "\n".join(reversed(to_return))
    
    
def is_lounge(ctx):
    if isinstance(ctx, str):
        return str(MKW_LOUNGE_GUILD_ID) == ctx or (str(TESTING_SERVER_ID) == ctx if TESTING else False)
    elif isinstance(ctx, int):
        return MKW_LOUNGE_GUILD_ID == ctx or (TESTING_SERVER_ID == ctx if TESTING else False)
    return get_guild_id(ctx) == MKW_LOUNGE_GUILD_ID or (get_guild_id(ctx) == ctx if TESTING else False)

    
def get_guild_id(ctx):
    if SERVER_ID_TO_IMPERSONATE is None:
        return ctx.guild.id
    return SERVER_ID_TO_IMPERSONATE

async def getJSONData(full_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(full_url) as r:
            if r.status == 200:
                js = await r.json()
                return js

def isfloat(value:str):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def isint(value:str):
    try:
        int(value)
        return True
    except:
        return False


def get_member_info(member):
    return f"{member.mention} ({member.display_name} - {str(member)})"

def get_members_with_any_role_id(members, role_ids):
    to_return = set()
    for role_id in role_ids:
        to_return.update(get_members_with_role_id(members, role_id))
    return to_return

def get_members_with_role_id(members, role_id):
    to_return = set()
    for member in members:
        for role in member.roles:
            if role.id == role_id:
                to_return.add(member)
    return to_return
