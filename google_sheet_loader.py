'''
Created on Aug 5, 2021

@author: willg
'''
import gspread
gc = gspread.service_account(filename='credentials.json')

master_sheet_url = ""

WORKSHEET_NAME = "Master List"
SHEET_WORKING_RANGE = "A2:F"


def get_sheet_data():
    print(master_sheet_url)
    SPREADSHEET_ID = master_sheet_url.split("/d/")[1].split("/")[0]
    sheet = gc.open_by_key(SPREADSHEET_ID)
    cur_worksheet = sheet.worksheet(WORKSHEET_NAME)
    return cur_worksheet.get(SHEET_WORKING_RANGE)


