'''
Created on Aug 5, 2021

@author: willg
'''
from common import isint

class BadDataGiven(Exception):
    pass

class Player:
    def __init__(self, sheet_list):
        self.load_list(sheet_list)
        
    def load_list(self, sheet_list):
        sheet_list = ["" if item is None else item.strip() for item in sheet_list]
        self.name = None
        self.discord_id = None
        self.rt_mmr = None
        self.ct_mmr = None
        self.rt_lr = None
        self.ct_lr = None
        
        if len(sheet_list) > 0:
            self.name = sheet_list[0]
        
        if len(sheet_list) > 1:
            self.discord_id = sheet_list[1]
        
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
                
    def get_lookup_name(self):
        return get_lookup_name(self.name)
    
    def __str__(self):
        return f"Name: {self.name}, Discord ID: {self.discord_id}, RT MMR: {self.rt_mmr}, RT LR: {self.rt_lr}, CT MMR: {self.ct_mmr}, CT LR: {self.ct_lr}"
    
                
                
            
    
    

def get_lookup_name(name:str):
    return name.strip().lower().replace(" ", "")
        
        
    
        
        