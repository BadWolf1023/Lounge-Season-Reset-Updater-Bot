'''
Created on Aug 5, 2021

@author: willg
'''
from common import isint
from datetime import datetime

class BadDataGiven(Exception):
    pass

class Player:
    def __init__(self, sheet_list):
        self.load_list(sheet_list)
        
    def load_list(self, sheet_list):
        temp_sheet_list = []
        for item in sheet_list:
            if item is None:
                temp_sheet_list.append("")
            elif isinstance(item, str):
                temp_sheet_list.append(item.strip())
            else:
                temp_sheet_list.append(item)
        sheet_list = temp_sheet_list
        self.name = None
        self.discord_id = None
        self.rt_mmr = None
        self.ct_mmr = None
        self.rt_lr = None
        self.ct_lr = None
        self.rt_last_event = datetime.min
        self.ct_last_event = datetime.min
        self.rt_events_played = 0
        self.ct_events_played = 0
        
        if len(sheet_list) > 0:
            self.name = sheet_list[0]
        
        if len(sheet_list) > 1:
            if sheet_list[1] is None or sheet_list[1] == "":
                self.discord_id = None
            elif not isint(sheet_list[1]):
                raise BadDataGiven()
            else:
                self.discord_id = int(sheet_list[1])
        
        if len(sheet_list) > 2:
            if sheet_list[2] is None or sheet_list[2] == "":
                self.rt_mmr = None
            elif not isint(sheet_list[2]):
                raise BadDataGiven()
            else:
                self.rt_mmr = int(sheet_list[2])
        
        if len(sheet_list) > 3:
            if sheet_list[3] is None or sheet_list[3] == "":
                self.ct_mmr = None
            elif not isint(sheet_list[3]):
                raise BadDataGiven()
            else:
                self.ct_mmr = int(sheet_list[3])
        
        if len(sheet_list) > 4:
            if sheet_list[4] is None or sheet_list[4] == "":
                self.rt_lr = None
            elif not isint(sheet_list[4]):
                raise BadDataGiven()
            else:
                self.rt_lr = int(sheet_list[4])
                
        if len(sheet_list) > 5:
            if sheet_list[5] is None or sheet_list[5] == "":
                self.ct_lr = None
            elif not isint(sheet_list[5]):
                raise BadDataGiven()
            else:
                self.ct_lr = int(sheet_list[5])
                
        if len(sheet_list) > 6:
            if sheet_list[6] is None or sheet_list[6] == "":
                pass
            else:
                self.rt_last_event = sheet_list[6]
        
        if len(sheet_list) > 7:
            if sheet_list[7] is None or sheet_list[7] == "":
                pass
            else:
                self.ct_last_event = sheet_list[7]
                
        if len(sheet_list) > 8:
            if sheet_list[8] is None or sheet_list[8] == "":
                self.rt_events_played = 0
            elif not isint(sheet_list[8]):
                raise BadDataGiven()
            else:
                self.rt_events_played = int(sheet_list[8])
        
        if len(sheet_list) > 9:
            if sheet_list[9] is None or sheet_list[9] == "":
                self.ct_events_played = 0
            elif not isint(sheet_list[9]):
                raise BadDataGiven()
            else:
                self.ct_events_played = int(sheet_list[9])
                
    def get_lookup_name(self):
        return get_lookup_name(self.name)
    
    def __str__(self):
        return f"Name: {self.name}, Discord ID: {self.discord_id}, RT MMR: {self.rt_mmr}, RT LR: {self.rt_lr}, CT MMR: {self.ct_mmr}, CT LR: {self.ct_lr}"
    
                
                
            
    
    

def get_lookup_name(name:str):
    return name.strip().lower().replace(" ", "")
        
        
    
        
        