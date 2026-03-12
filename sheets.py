import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

COLUMNS = ["Имя", "Фамилия", "Email", "Телефон", "Компания", "Должность",
           "Сейлз", "Дата", "Источник", "Запрос", "Не звонить"]

def load_contacts(spreadsheet_id: str) -> list[dict]:
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A2:K"
    ).execute()

    values = result.get("values", [])
    contacts = []
    for row in values:
        row += [""] * (len(COLUMNS) - len(row))
        contact = dict(zip(COLUMNS, row))
        # Обрезаем время из даты: "2025-12-05 12:24:51" → "2025-12-05"
        if contact.get("Дата"):
            contact["Дата"] = str(contact["Дата"]).split(" ")[0]
        contacts.append(contact)
    return contacts
