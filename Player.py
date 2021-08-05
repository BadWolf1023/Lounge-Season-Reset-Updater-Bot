'''
Created on Aug 5, 2021

@author: willg
'''

class BadDataGiven(Exception):
    pass

class Player:
    def __init__(self, sheet_list):
        self.load_list(sheet_list)
        
    def load_list(self, sheet_list):
        sheet_list = [item.strip() for item in sheet_list]
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
            if sheet_list[2] == "":
                self.rt_mmr = None
            elif not sheet_list[2].isnumeric():
                raise BadDataGiven()
            else:
                self.rt_mmr = int(sheet_list[2])
        
        if len(sheet_list) > 3:
            if sheet_list[3] == "":
                self.ct_mmr = None
            elif not sheet_list[3].isnumeric():
                raise BadDataGiven()
            else:
                self.ct_mmr = int(sheet_list[3])
        
        if len(sheet_list) > 4:
            if sheet_list[4] == "":
                self.rt_lr = None
            elif not sheet_list[4].isnumeric():
                raise BadDataGiven()
            else:
                self.rt_lr = int(sheet_list[4])
                
        if len(sheet_list) > 5:
            if sheet_list[5] == "":
                self.ct_lr = None
            elif not sheet_list[5].isnumeric():
                raise BadDataGiven()
            else:
                self.ct_lr = int(sheet_list[5])
                
    def get_lookup_name(self):
        return get_lookup_name(self.name)
    
                
                
            
    
    

def get_lookup_name(name:str):
    return name.strip().lower().replace(" ", "")
        
        
    
        
        