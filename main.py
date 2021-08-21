'''
Created on Aug 5, 2021

@author: willg
'''
import discord
import google_sheet_loader
import website_api_loader
import Player

invite_link = "https://discord.com/api/oauth2/authorize?client_id=872936275320139786&permissions=268470272&scope=bot"
lounge_server_id = 387347467332485122
running_channel_id = 775477321498361927

dont_modify_roles = False
finished_on_ready = False
USING_SHEET = False


def load_private_data():
    global master_sheet_url
    global bot_key
    
    with open("private.txt") as f:
        all_lines = f.readlines()
        google_sheet_loader.master_sheet_url = all_lines[0]
        bot_key = all_lines[1]
        
load_private_data()
loaded_player_data = google_sheet_loader.get_sheet_data() if USING_SHEET else website_api_loader.get_player_data()
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
                         (5499, "RT Class C", 871739875383181333),
                         (6499, "RT Class B", 871739761574969384),
                         (7449, "RT Class A", 871739726065963008),
                         (8999, "RT Class S", 871739972313575465),
                         (None, "RT Class X", 871740024155168829)]

CT_CLASS_ROLE_CUTOFFS = [(999, "CT Class F", 871740200215281744),
                         (2249, "CT Class E", 871739950457040916),
                         (3249, "CT Class D", 871740313444704296),
                         (4999, "CT Class C", 871739900393844776),
                         (5999, "CT Class B", 871739853237264404),
                         (7249, "CT Class A", 871739791203524608),
                         (8749, "CT Class S", 871740002051174400),
                         (None, "CT Class X", 871740054781976587)]

#For players to get an updated RT Ranking role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = {data[2] for data in RT_RANKING_ROLE_CUTOFFS}
#For players to get an updated CT Ranking role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE = {data[2] for data in CT_RANKING_ROLE_CUTOFFS}
#For players to get an updated RT Class role, they must have one of these role IDs first
RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = {data[2] for data in RT_CLASS_ROLE_CUTOFFS}
#For players to get an updated CT Class role, they must have one of these role IDs first
CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE = {data[2] for data in CT_CLASS_ROLE_CUTOFFS}

def has_any_role_id(member:discord.Member, role_ids):
    for role in member.roles:
        if role.id in role_ids:
            return True
    return False

def determine_new_role(player_rating, cutoff_data):
    for cutoff in cutoff_data:
        if cutoff[0] is None or player_rating < cutoff[0]:
            return cutoff[2]
    return None

def get_roles_to_remove(member, guild, role_ids_to_remove):
    roles_to_remove = []
    for role in member.roles:
        if role.id in role_ids_to_remove:
            roles_to_remove.append(role)
    return roles_to_remove

def discard_role_from(role_to_discard, roles):
    to_discard = []
    for ind, role in enumerate(roles):
        if role_to_discard.id == role.id:
            to_discard.append(ind)
            
    to_discard.sort(reverse=True)
    for index in to_discard:
        roles.pop(index)
    return roles

def has_role(member:discord.Member, role_to_find):
    for role in member.roles:
        if role.id == role_to_find.id:
            return True
    return False
            
    
async def __update_roles__(running_channel, guild, rating_func, previous_role_ids, cutoff_data, remove_old_role=False, track_type="RT", role_type="Class"):
    members = guild.members[:500] if dont_modify_roles else guild.members
    
    to_send = []
    to_send_counter = 0
    for ind, member in enumerate(members):
        if ind % 300 == 0:
            await running_channel.send(f"---- {int(ind/len(members) * 100)}% finished with {track_type} {role_type} role updating.")
        if has_any_role_id(member, previous_role_ids):
            #Need to update since they have previous role IDs
            lookup_name = Player.get_lookup_name(member.display_name)
            
            if lookup_name not in all_player_data:
                await running_channel.send(f"---- {member.mention} has previous {track_type} roles, but I can't find them on the {'Google Sheet' if USING_SHEET else 'Website'}.")
                continue

            sheet_player = all_player_data[lookup_name]
            player_rating = rating_func(sheet_player)
            if player_rating is None:
                await running_channel.send(f"---- {member.mention} has previous {track_type} roles, but their {track_type} rating on {'Google Sheet' if USING_SHEET else 'the Website'} is blank or invalid.")
                continue
        
            new_role_id = determine_new_role(player_rating, cutoff_data)
            if new_role_id is None:
                await running_channel.send(f"---- {member.mention} could not determine new role ID for some reason, player rating is {player_rating}")
                continue
            
            new_role_obj = guild.get_role(new_role_id)
            if new_role_obj is None:
                await running_channel.send(f"---- {member.mention} could not find the following role ID in the server: {new_role_id}")
                continue
            
            if remove_old_role:
                roles_to_remove = get_roles_to_remove(member, guild, previous_role_ids)
                if len(roles_to_remove) == 0:
                    await running_channel.send(f"---- {member.mention} had no previous roles to remove. This shouldn't be possible.")
                    continue
                
                #The above 3 lines ensure that they have a role to remove
                #The 3 lines below throw out the new role from that list and check if we need to remove anything
                #If we don't need to remove anything, don't
                discard_role_from(new_role_obj, roles_to_remove)
                if len(roles_to_remove) == 0:
                    continue
                
                if not dont_modify_roles:
                    try:
                        await member.remove_roles(*roles_to_remove, reason=None, atomic=True)
                    except:
                        await running_channel.send(f"---- {member.mention} could not remove roles: {','.join([role.name for role in roles_to_remove])} - Discord Exception")
                        continue
                    
                    await running_channel.send(f"{member.mention} removed roles: {','.join([role.name for role in roles_to_remove])}")
                else:
                    await running_channel.send(f"{member.mention} would remove roles: {','.join([role.name for role in roles_to_remove])}")
                    
                        
            #If they already have the role, don't bother wasting an API call to add it
            if has_any_role_id(member, [new_role_obj.id]):
                continue
            
            if dont_modify_roles:
                await running_channel.send(f"{member.mention} would add roles: {new_role_obj.name}")
                pass
            else:
                try:
                    await member.add_roles(new_role_obj, reason=None, atomic=True)
                except:
                    await running_channel.send(f"---- {member.mention} could not add roles: {new_role_obj.name} - Discord Exception")
                
                
                await running_channel.send(f"{member.mention} added roles: {new_role_obj.name}")

                
            
            
                
        

async def update_roles(running_channel, guild):
    await running_channel.send(f"Lounge server has {len(guild.members)} members.")
    
    await running_channel.send("--------------- Updating RT Class Roles ---------------")
    rt_class_rating_func = lambda p: p.rt_mmr
    await __update_roles__(running_channel, guild, rt_class_rating_func, RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE, RT_CLASS_ROLE_CUTOFFS, True, track_type="RT", role_type="Class")
    
    await running_channel.send("--------------- Updating CT Class Roles ---------------")
    ct_class_rating_func = lambda p: p.ct_mmr
    await __update_roles__(running_channel, guild, ct_class_rating_func, CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE, CT_CLASS_ROLE_CUTOFFS, True, track_type="CT", role_type="Class")
    
    await running_channel.send("--------------- Updating RT Ranking Roles ---------------")
    rt_role_rating_func = lambda p: p.rt_lr
    await __update_roles__(running_channel, guild, rt_role_rating_func, RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE, RT_RANKING_ROLE_CUTOFFS, True, track_type="RT", role_type="Ranking")
    
    await running_channel.send("--------------- Updating CT Ranking Roles ---------------")
    ct_role_rating_func = lambda p: p.ct_lr
    await __update_roles__(running_channel, guild, ct_role_rating_func, CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE, CT_RANKING_ROLE_CUTOFFS, True, track_type="CT", role_type="Ranking")
    
    
        
    
    
async def read_player_data_in(running_channel):
    all_player_data.clear()
    # Call the Sheets API
    for player_data in loaded_player_data:
        if len(player_data) == 0:
            continue
        
        if len(player_data) > 0:
            try:
                cur_player = Player.Player(player_data)
                lookup_name = cur_player.get_lookup_name()
                if lookup_name in all_player_data:
                    await running_channel.send(f"Warning: Duplicate player: {cur_player.name}")
                else:
                    all_player_data[lookup_name] = cur_player
            except Player.BadDataGiven:
                await running_channel.send(f"This data received contains bad data: {player_data}")
    await running_channel.send(f"Read in {len(all_player_data)} players.\nData source (sheet or API) has a total of {len(loaded_player_data)} players.")
    
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
        await running_channel.send("Hello, I'm back to automate your role removal and addition process. Please pay me, my 1's and 0's work so hard.")
        await running_channel.send(f"I am now running. I **will {'NOT' if dont_modify_roles else ''}** be modifying roles in this server for this run.")
    except:
        print("I can't see the bots channel that I'm supposed to be running in.")
        return
    
    await running_channel.send("Updating roles started.")
    
    await read_player_data_in(running_channel)
    
    await update_roles(running_channel, lounge_server)
    
    
    if dont_modify_roles:
        await running_channel.send("Testing ended.")
    else:
        await running_channel.send("Finished updating roles.")
    
    
    
    


client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_ready():
    global finished_on_ready
    if not finished_on_ready:
        await main()
        finished_on_ready = True


client.run(bot_key)
    




