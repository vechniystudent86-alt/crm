"""
Шаблоны абонементов Zumba CRM
Стандартные тарифы студии
"""

SUBSCRIPTION_TEMPLATES = [
    {
        "name": "Пробная тренировка",
        "visits_total": 1,
        "price": 500.0,
        "description": "Первое пробное занятие"
    },
    {
        "name": "Разовое посещение",
        "visits_total": 1,
        "price": 750.0,
        "description": "Однократное посещение без абонемента"
    },
    {
        "name": "4 занятия",
        "visits_total": 4,
        "price": 2800.0,
        "description": "Абонемент на 4 занятия (700₽ за занятие)",
        "validity_days": 30  # Действует 30 дней
    },
    {
        "name": "6 занятий",
        "visits_total": 6,
        "price": 3900.0,
        "description": "Абонемент на 6 занятий (650₽ за занятие)",
        "validity_days": 45  # Действует 45 дней
    },
    {
        "name": "8 занятий",
        "visits_total": 8,
        "price": 4800.0,
        "description": "Абонемент на 8 занятий (600₽ за занятие)",
        "validity_days": 60  # Действует 60 дней
    },
]


def get_template_by_name(name: str) -> dict | None:
    """Получить шаблон по названию"""
    for template in SUBSCRIPTION_TEMPLATES:
        if template["name"].lower() == name.lower():
            return template
    return None


def get_all_templates() -> list:
    """Получить все шаблоны"""
    return SUBSCRIPTION_TEMPLATES


def calculate_price_per_visit(template: dict) -> float:
    """Рассчитать стоимость одного занятия"""
    return template["price"] / template["visits_total"]
