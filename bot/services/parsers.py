import re
from datetime import datetime, timedelta, time
from typing import Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class TimeParseResult:
    time_str: Optional[str] = None
    is_ambiguous: bool = False
    suggestions: Optional[List[str]] = None
    error: Optional[str] = None

@dataclass
class DateParseResult:
    date_obj: Optional[datetime] = None
    date_str: Optional[str] = None
    error: Optional[str] = None

def normalize_time_input(raw: str) -> TimeParseResult:
    raw = raw.lower().strip()

    if any(word in raw for word in ["вечер", "после обед"]):
        return TimeParseResult(is_ambiguous=True, suggestions=["16:00–18:00", "18:00–20:00", "20:00–22:00"])

    # Регулярки для форматов
    # 18:30, 18.30, 18 30, 1830
    time_pattern = re.compile(r'(\d{1,2})[:.\s]?(\d{2})?')
    match = time_pattern.search(raw)
    
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        
        if hours > 23 or minutes > 59:
            return TimeParseResult(error="Неверный формат времени.")
            
        # "в 6" / "к 6" для доставки чаще означает вечер; подтверждаем, но не выбираем молча.
        if hours < 10 and hours > 0 and (raw.startswith("в ") or raw.startswith("к ")):
            return TimeParseResult(is_ambiguous=True, suggestions=[f"{hours+12:02d}:00"])

        return TimeParseResult(time_str=f"{hours:02d}:{minutes:02d}")

    return TimeParseResult(error="Не смог распознать время.")

def normalize_date_input(raw: str, now: datetime = None) -> DateParseResult:
    if not now:
        now = datetime.now()
        
    raw = raw.lower().strip()
    
    if "сегодня" in raw:
        return DateParseResult(date_obj=now, date_str=now.strftime("%d.%m"))
    if "завтра" in raw:
        tomorrow = now + timedelta(days=1)
        return DateParseResult(date_obj=tomorrow, date_str=tomorrow.strftime("%d.%m"))
        
    # Дни недели
    days_map = {
        "понедельник": 0, "вт": 1, "сред": 2, "четв": 3, "пятн": 4, "субб": 5, "воскр": 6
    }
    for day_name, day_idx in days_map.items():
        if day_name in raw:
            days_ahead = day_idx - now.weekday()
            if days_ahead <= 0: # Если день уже прошел или сегодня, берем следующую неделю
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
            return DateParseResult(date_obj=target_date, date_str=target_date.strftime("%d.%m"))

    # Форматы 15.05, 15/05, 15 мая
    date_pattern = re.compile(r'(\d{1,2})[./\s]?(\d{1,2}|[а-я]+)')
    match = date_pattern.search(raw)
    
    if match:
        day = int(match.group(1))
        month_raw = match.group(2)
        
        months_map = {
            "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "мая": 5,
            "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12
        }
        
        if month_raw.isdigit():
            month = int(month_raw)
        else:
            month = 0
            for m_name, m_idx in months_map.items():
                if m_name in month_raw:
                    month = m_idx
                    break
        
        if month < 1 or month > 12:
            return DateParseResult(error="Неверный месяц.")
            
        try:
            target_date = datetime(now.year, month, day)
            if target_date.date() < now.date():
                return DateParseResult(error="Дата уже прошла.")
                
            return DateParseResult(date_obj=target_date, date_str=target_date.strftime("%d.%m"))
        except ValueError:
            return DateParseResult(error="Неверная дата.")

    return DateParseResult(error="Не смог распознать дату.")
