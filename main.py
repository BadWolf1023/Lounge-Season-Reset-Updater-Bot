'''
Created on Aug 5, 2021

@author: willg
'''
import discord
import google_sheet_loader
import Player

invite_link = "https://discord.com/api/oauth2/authorize?client_id=872936275320139786&permissions=268470272&scope=bot"
lounge_server_id = 387347467332485122
running_channel_id = 775477321498361927

dont_modify_roles = True
finished_on_ready = False


def load_private_data():
    global master_sheet_url
    global bot_key
    
    with open("private.txt") as f:
        all_lines = f.readlines()
        google_sheet_loader.master_sheet_url = all_lines[0]
        bot_key = all_lines[1]
        
load_private_data()
mmr_sheet = google_sheet_loader.get_sheet_data()
all_player_data = {}



#These are the cutoffs. If a player has less than or equal to the first number tuple, they will receive this role
#Currently, for S7, this number is the current season's LR
RT_RANKING_ROLE_CUTOFFS = [(1249, "RT Iron", 721162930456100935),
                         (2499, "RT Bronze", 389456781698400258),
                         (3749, "RT Silver", 667780593504878602),
                         (4999, "RT Gold", 667780534084173836),
                         (6499, "RT Platinum", 434562700740132874),
                         (7999, "RT Emerald", 799030242643017802),
                         (9499, "RT Ruby", 835170073785270283),
                         (10999, "RT Diamond", 387348621189840906),
                         (11999, "RT Master", 387348971699568642),
                         (None, "RT Grandmaster", 800957400672501770)]

CT_RANKING_ROLE_CUTOFFS = [(1249, "CT Iron", 721162976354238534),
                         (2249, "CT Bronze", 521027322846117890),
                         (3499, "CT Silver", 684567072856080404),
                         (4749, "CT Gold", 521028250424573962),
                         (6249, "CT Platinum", 520796951445504000),
                         (7499, "CT Emerald", 800956334123909130),
                         (8999, "CT Ruby", 871975113250181180),
                         (10999, "CT Diamond", 521028390719848468),
                         (11999, "CT Master", 520796895962988591),
                         (None, "CT Grandmaster", 800957596780724244)]


#These are the cutoffs. If a player has less than or equal to the first number tuple
#Currently, for S7, this number is the previous season's MMR
RT_CLASS_ROLE_CUTOFFS = [(999, "RT Class F", 871740169290674236),
                         (2499, "RT Class E", 871740123182690314),
                         (3999, "RT Class D", 871739925794525185),
                         (4749, "RT Class C", 871739875383181333),
                         (5499, "RT Class B", 871739761574969384),
                         (6999, "RT Class A", 871739726065963008),
                         (8499, "RT Class S", 871739972313575465),
                         (None, "RT Class X", 871740024155168829)]

CT_CLASS_ROLE_CUTOFFS = [(999, "CT Class F", 871740200215281744),
                         (2249, "CT Class E", 871739950457040916),
                         (3249, "CT Class D", 871740313444704296),
                         (4499, "CT Class C", 871739900393844776),
                         (5249, "CT Class B", 871739853237264404),
                         (6749, "CT Class A", 871739791203524608),
                         (8249, "CT Class S", 871740002051174400),
                         (None, "CT Class X", 871740054781976587)]

#For players to get an updated RT Ranking role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = {}
#For players to get an updated CT Ranking role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = {}
#For players to get an updated RT Class role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = {}
#For players to get an updated CT Class role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = {}

def has_any_role_id(member:discord.Member, role_ids):
    for role in member.roles:
        if role.id in role_ids:
            return True
    return False

def determine_new_role(sheet_player_rating, cutoff_data):
    for cutoff in cutoff_data:
        if cutoff[0] is None or sheet_player_rating < cutoff[0]:
            return cutoff[2]
    return None

async def get_roles_to_remove(member, guild, role_ids_to_remove):
    roles_to_remove = []
    for role in member.roles:
        if role.id in role_ids_to_remove:
            roles_to_remove.append(role)
    return roles_to_remove
    
async def __update_roles__(running_channel, guild, rating_func, previous_role_ids, cutoff_data, remove_old_role=False):
    for member in guild.members:
        if has_any_role_id(member, previous_role_ids):
            #Need to update since they have previous role IDs
            lookup_name = Player.get_lookup_name(member.display_name)
            
            if lookup_name not in all_player_data:
                await running_channel.send(f"{member.mention} has previous roles that allow them to see echelons, but I can't find them on the Google Sheet.")
                continue

            sheet_player = all_player_data[lookup_name]
            sheet_player_rating = rating_func(sheet_player)
            if sheet_player_rating is None:
                await running_channel.send(f"{member.mention} has previous roles that allow them to see echelons, but their rating on Google Sheets is blank or invalid.")
                continue
        
            new_role_id = determine_new_role(sheet_player_rating, cutoff_data)
            if new_role_id is None:
                await running_channel.send(f"{member.mention} could not determine new role ID for some reason, player rating is {sheet_player_rating}")
                continue
            
            new_role_obj = guild.get_role(new_role_id)
            if new_role_obj is None:
                await running_channel.send(f"{member.mention} could not find the following role ID in the server: {new_role_id}")
                continue
            
            if remove_old_role:
                roles_to_remove = get_roles_to_remove(member, guild, previous_role_ids)
                if not dont_modify_roles:
                    await running_channel.send(f"{member.mention} removed roles: {','.join([role.name for role in roles_to_remove])}")
                    #TODO: Fix
                else:
                    await running_channel.send(f"{member.mention} would remove roles: {','.join([role.name for role in roles_to_remove])}")
                    
                
            
            
                
        

async def update_roles(running_channel, guild):
    await running_channel.send(f"Lounge server has {len(guild.members)} members.")
    
    
        
    
    
async def read_player_data_in(running_channel):
    all_player_data.clear()
    # Call the Sheets API
    for player_data in mmr_sheet:
        if len(player_data) == 0:
            continue
        
        if len(player_data) > 0:
            try:
                cur_player = Player.Player(player_data)
                lookup_name = cur_player.get_lookup_name()
                if lookup_name in all_player_data:
                    await running_channel.send(f"Warning: Duplicate player on Google Sheet: {cur_player.name}")
                else:
                    all_player_data[lookup_name] = cur_player
            except Player.BadDataGiven:
                await running_channel.send(f"This data received from the sheet contains bad data: {player_data}")
    await running_channel.send(f"Read in {len(all_player_data)} players from Google Sheet.\nGoogle Sheet has a total of {len(mmr_sheet)} players.")
    
async def main(server_id=lounge_server_id):
    lounge_server = client.get_guild(server_id)
    if lounge_server is None:
        print("I'm not in the Lounge server.")
        return
    
    running_channel = client.get_channel(running_channel_id)
    if running_channel is None:
        print("I'm not in the Lounge server.")
        return
    
    try:
        await running_channel.send("Hello, I am a slave bot dedicated to updating roles at season reset!")
        await running_channel.send(f"I am now running. I **will {'NOT' if dont_modify_roles else ''}** be modifying roles in this server for this run.")
    except:
        print("I can't see the bots channel that I'm supposed to be running in.")
        return
    
    
    await read_player_data_in(running_channel)
    
    await update_roles(running_channel, lounge_server)
    
    
    if dont_modify_roles:
        await running_channel.send("Testing ended.")
    
    
    
    


client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_ready():
    global finished_on_ready
    if not finished_on_ready:
        await main()
        finished_on_ready = True


client.run(bot_key)
    




