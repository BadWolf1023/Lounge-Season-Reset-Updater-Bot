'''
Created on Aug 5, 2021

@author: willg
'''
def load_private_data():
    global master_sheet_url
    global bot_key
    
    with open("private.txt") as f:
        all_lines = f.readlines()
        _, master_sheet_url = all_lines[0].split(":")
        _, bot_key = all_lines[1].split(":")
        
load_private_data()

"""x: 871740024155168829
s: 871739972313575465
a: 871739726065963008
b: 871739761574969384
c: 871739875383181333
d: 871739925794525185
e: 871740123182690314
f: 871740169290674236

ct classes:
x: 871740054781976587
s: 871740002051174400
a: 871739791203524608
b: 871739853237264404
c: 871739900393844776
d: 871740313444704296
e: 871739950457040916
f: 871740200215281744"""
