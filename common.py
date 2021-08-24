'''
Created on Aug 21, 2021

@author: willg
'''

import aiohttp
TESTING_SERVER_ID = 739733336871665696
BAD_WOLF_ID = 706120725882470460
TESTING=True
MKW_LOUNGE_GUILD_ID = 387347467332485122
    
DISCORD_MAX_MESSAGE_LEN = 2000
SERVER_ID_TO_IMPERSONATE = None


#These are the cutoffs. If a player has less than or equal to the first number tuple, they will receive this role
#Currently, for S7, this number is the current season's LR
RT_RANKING_ROLE_CUTOFFS = []

CT_RANKING_ROLE_CUTOFFS = []


#These are the cutoffs. If a player has less than or equal to the first number tuple
#Currently, for S7, this number is the previous season's MMR
RT_CLASS_ROLE_CUTOFFS = []

CT_CLASS_ROLE_CUTOFFS = []

#For players to get an updated RT Ranking role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = set()
#For players to get an updated CT Ranking role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = set()
#For players to get an updated RT Class role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = set()
#For players to get an updated CT Class role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = set()

all_player_data = {}


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
    except ValueError:
        return False
