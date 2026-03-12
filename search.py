import re

def normalize(s: str) -> str:
    return s.lower().strip() if s else ""

def fuzzy_match(query: str, value: str, threshold: int = 70) -> bool:
    """Простой нечёткий поиск: совпадение по подстроке с учётом опечаток."""
    q = normalize(query)
    v = normalize(value)
    if not q or not v:
        return False
    # Прямое вхождение
    if q in v or v in q:
        return True
    # Поиск по словам (каждое слово запроса должно быть в значении)
    words = q.split()
    return all(w in v for w in words if len(w) > 2)

def find_contacts(contacts: list[dict], params: dict) -> list[dict]:
    results = []
    for c in contacts:
        match = True
        if params.get("name"):
            full_name = f"{c.get('Имя','')} {c.get('Фамилия','')}".strip()
            if not fuzzy_match(params["name"], full_name):
                match = False
        if params.get("company"):
            if not fuzzy_match(params["company"], c.get("Компания", "")):
                match = False
        if params.get("position"):
            if not fuzzy_match(params["position"], c.get("Должность", "")):
                match = False
        if params.get("email"):
            if normalize(params["email"]) not in normalize(c.get("Email", "")):
                match = False
        if params.get("phone"):
            phone_q = re.sub(r"\D", "", params["phone"])
            phone_c = re.sub(r"\D", "", c.get("Телефон", ""))
            if phone_q not in phone_c:
                match = False
        if match:
            results.append(c)
    return results
