import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CREDS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")

COLUMNS = ["Имя", "Фамилия", "Email", "Телефон", "Компания", "Должность",
           "Сейлз", "Дата", "Источник", "Запрос", "Не звонить"]

def load_contacts(spreadsheet_id: str) -> list[dict]:
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A2:K"  # пропускаем заголовок, берём все строки
    ).execute()

    values = result.get("values", [])
    contacts = []
    for row in values:
        # Дополняем строку до нужной длины
        row += [""] * (len(COLUMNS) - len(row))
        contact = dict(zip(COLUMNS, row))
        contacts.append(contact)
    return contacts
