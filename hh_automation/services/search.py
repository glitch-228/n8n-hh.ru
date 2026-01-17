"""Асинхронный сервис поиска вакансий."""

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

from playwright.async_api import Page

from ..config import get_settings
from .browser import browser_manager

logger = logging.getLogger(__name__)

WORK_FORMAT_MAP = {
    "удалённо": "REMOTE",
    "удаленно": "REMOTE",
    "remote": "REMOTE",
    "в офисе": "ON_SITE",
    "офис": "ON_SITE",
    "office": "ON_SITE",
    "гибрид": "HYBRID",
    "hybrid": "HYBRID",
    "разъездной": "FIELD_WORK",
    "field": "FIELD_WORK",
    "field work": "FIELD_WORK",
    "field_work": "FIELD_WORK",
}

EXPERIENCE_MAP = {
    "нет опыта": "noExperience",
    "noexperience": "noExperience",
    "1-3": "between1And3",
    "от 1 до 3": "between1And3",
    "between1and3": "between1And3",
    "3-6": "between3And6",
    "от 3 до 6": "between3And6",
    "between3and6": "between3And6",
    "более 6": "moreThan6",
    "morethan6": "moreThan6",
}


def _map_filter_value(value: Optional[str], mapping: dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return mapping.get(normalized, value.strip())


def _normalize_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


@dataclass
class Vacancy:
    """Модель данных вакансии."""
    title: str
    url: str
    employer: str
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "employer": self.employer,
            "description": self.description
        }


class VacancySearchService:
    """Сервис для поиска вакансий на HH.ru."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def _get_vacancy_description(self, page: Page, url: str) -> str:
        """
        Переход на страницу вакансии и извлечение полного описания.
        
        Аргументы:
            page: Страница браузера для использования.
            url: URL вакансии.
            
        Возвращает:
            Полный текст описания вакансии.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("[data-qa='vacancy-description']", timeout=10000)
            
            description_el = page.locator("[data-qa='vacancy-description']")
            if await description_el.count() > 0:
                return (await description_el.inner_text()).strip()
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to get description for {url}: {e}")
            return ""

    async def _check_bot_protection(self, page: Page) -> bool:
        """Проверка, сработала ли защита от ботов (капча)."""
        title = await page.title()
        content = await page.content()
        return "captcha" in title.lower() or "robot" in content.lower()

    async def search(
        self,
        query: Optional[str] = None,
        page_num: int = 0,
        work_format: Optional[str] = None,
        experience: Optional[str] = None,
        search_field: Optional[str] = None,
        order_by: Optional[str] = None,
        employment: Optional[str] = None,
        schedule: Optional[str] = None,
        education_level: Optional[str] = None,
        employment_form: Optional[str] = None,
        working_hours: Optional[str] = None,
        work_schedule_by_days: Optional[str] = None,
        salary: Optional[str] = None,
        currency: Optional[str] = None,
        salary_per_mode: Optional[str] = None,
        salary_frequency: Optional[str] = None,
        only_with_salary: Optional[str] = None,
        label: Optional[str] = None,
        driver_license_types: Optional[str] = None,
        accept_temporary: Optional[str] = None
    ) -> list[dict]:
        """
        Поиск вакансий, соответствующих запросу.
        
        Аргументы:
            query: Текст запроса. По умолчанию используется значение из настроек.
            page_num: Номер страницы для пагинации (начиная с 0).
            work_format: Формат работы (например, "удалённо").
            experience: Опыт работы (например, "нет опыта").
            search_field: Поле поиска (name|company_name|description).
            order_by: Сортировка (publication_time|salary_desc|salary_asc|relevance|distance).
            employment: Тип занятости (full|part|project|volunteer|probation).
            schedule: График работы (fullDay|shift|flexible|remote|flyInFlyOut).
            education_level: Уровень образования.
            employment_form: Форма занятости.
            working_hours: Рабочие часы.
            work_schedule_by_days: График по дням.
            salary: Зарплата (целое число).
            currency: Валюта зарплаты.
            salary_per_mode: Период зарплаты.
            salary_frequency: Частота выплат.
            only_with_salary: Только с зарплатой (true|false).
            label: Метки вакансий.
            driver_license_types: Типы водительских прав.
            accept_temporary: Временная занятость (true|false).
            
        Возвращает:
            Список словарей вакансий с заголовком, URL, работодателем и описанием.
            
        Исключения:
            RuntimeError: Если сработала защита от ботов.
            FileNotFoundError: Если файл сессии не найден.
        """
        query = query or self._settings.default_search_text
        work_format = work_format or self._settings.default_work_format
        experience = experience or self._settings.default_experience

        work_format_value = _map_filter_value(work_format, WORK_FORMAT_MAP)
        experience_value = _map_filter_value(experience, EXPERIENCE_MAP)

        logger.info(
            "Searching vacancies: query='%s', page=%s, work_format='%s', experience='%s'",
            query,
            page_num,
            work_format_value,
            experience_value
        )

        async with browser_manager.get_page(use_session=True) as page:
            # Сборка URL для поиска
            params = {
                "text": query,
                "area": self._settings.area_code,
                "items_on_page": 20,
                "page": page_num
            }
            if work_format_value:
                params["work_format"] = work_format_value
            if experience_value:
                params["experience"] = experience_value
            extra_params = {
                "search_field": search_field,
                "order_by": order_by,
                "employment": employment,
                "schedule": schedule,
                "education_level": education_level,
                "employment_form": employment_form,
                "working_hours": working_hours,
                "work_schedule_by_days": work_schedule_by_days,
                "salary": salary,
                "currency": currency,
                "salary_per_mode": salary_per_mode,
                "salary_frequency": salary_frequency,
                "only_with_salary": only_with_salary,
                "label": label,
                "driver_license_types": driver_license_types,
                "accept_temporary": accept_temporary,
            }
            for key, value in extra_params.items():
                normalized = _normalize_param(value)
                if normalized is not None:
                    params[key] = normalized

            url = f"https://hh.ru/search/vacancy?{urlencode(params)}"
            
            await page.goto(url, wait_until="domcontentloaded")
            
            if await self._check_bot_protection(page):
                raise RuntimeError("Bot protection triggered (captcha detected)")

            # Ожидание результатов
            await page.wait_for_selector("[data-qa='vacancy-serp__vacancy']", timeout=10000)
            
            # Сбор основных данных вакансий из результатов поиска
            vacancy_data: list[dict] = []
            cards = await page.locator("[data-qa='vacancy-serp__vacancy']").all()
            
            for i, card in enumerate(cards):
                try:
                    title_el = card.locator("[data-qa='serp-item__title']")
                    await title_el.wait_for(state="visible", timeout=5000)
                    
                    href = await title_el.get_attribute("href")
                    title = await title_el.inner_text()
                    
                    employer_el = card.locator("[data-qa='vacancy-serp__vacancy-employer']").first
                    employer = (
                        await employer_el.inner_text() 
                        if await employer_el.count() > 0 
                        else "Unknown"
                    )
                    
                    vacancy_data.append({
                        "title": title,
                        "url": href,
                        "employer": employer
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to parse vacancy card {i}: {e}")
                    continue

            # Получение полных описаний для каждой вакансии
            vacancies: list[dict] = []
            for data in vacancy_data:
                description = await self._get_vacancy_description(page, data["url"])
                vacancy = Vacancy(
                    title=data["title"],
                    url=data["url"],
                    employer=data["employer"],
                    description=description
                )
                vacancies.append(vacancy.to_dict())

            logger.info(f"Found {len(vacancies)} vacancies")
            return vacancies
