import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .config import get_settings
from .services import browser_manager, VacancySearchService, VacancyApplyService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("HHServer")
settings = get_settings()


class ApplyRequest(BaseModel):
    """Тело запроса для отклика на вакансию."""
    url: HttpUrl
    message: str = ""


class ApplyResponse(BaseModel):
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting browser manager...")
    await browser_manager.start()
    yield
    logger.info("Shutting down browser manager...")
    await browser_manager.stop()


app = FastAPI(
    title="HH.ru Automation API",
    description="Async API for searching and applying to vacancies on HH.ru",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Экземпляры сервисов
search_service = VacancySearchService()
apply_service = VacancyApplyService()


@app.get("/search")
async def search_vacancies(
    text: str = Query(default=settings.default_search_text, description="Search query text"),
    page: int = Query(default=0, ge=0, description="Page number (0-indexed)"),
    work_format: str = Query(
        default=settings.default_work_format,
        description="Work format (например, удалённо)"
    ),
    experience: str = Query(
        default=settings.default_experience,
        description="Experience (например, нет опыта)"
    ),
    search_field: Optional[str] = Query(default=None, description="Search field (name|company_name|description)"),
    order_by: Optional[str] = Query(
        default=None,
        description="Order by (publication_time|salary_desc|salary_asc|relevance|distance)"
    ),
    employment: Optional[str] = Query(default=None, description="Employment (full|part|project|volunteer|probation)"),
    schedule: Optional[str] = Query(default=None, description="Schedule (fullDay|shift|flexible|remote|flyInFlyOut)"),
    education_level: Optional[str] = Query(default=None, description="Education level"),
    employment_form: Optional[str] = Query(default=None, description="Employment form"),
    working_hours: Optional[str] = Query(default=None, description="Working hours"),
    work_schedule_by_days: Optional[str] = Query(default=None, description="Work schedule by days"),
    salary: Optional[str] = Query(default=None, description="Salary"),
    currency: Optional[str] = Query(default=None, description="Currency"),
    salary_per_mode: Optional[str] = Query(default=None, description="Salary per mode"),
    salary_frequency: Optional[str] = Query(default=None, description="Salary frequency"),
    only_with_salary: Optional[str] = Query(default=None, description="Only with salary (true|false)"),
    label: Optional[str] = Query(default=None, description="Labels"),
    driver_license_types: Optional[str] = Query(default=None, description="Driver license types"),
    accept_temporary: Optional[str] = Query(default=None, description="Accept temporary (true|false)")
) -> list[dict]:
    """
    Поиск вакансий на HH.ru.
    
    Возвращает список вакансий с заголовком, URL, работодателем и описанием.
    """
    logger.info(
        "Search request: text='%s', page=%s, work_format='%s', experience='%s'",
        text,
        page,
        work_format,
        experience
    )
    
    try:
        vacancies = await search_service.search(
            query=text,
            page_num=page,
            work_format=work_format,
            experience=experience,
            search_field=search_field,
            order_by=order_by,
            employment=employment,
            schedule=schedule,
            education_level=education_level,
            employment_form=employment_form,
            working_hours=working_hours,
            work_schedule_by_days=work_schedule_by_days,
            salary=salary,
            currency=currency,
            salary_per_mode=salary_per_mode,
            salary_frequency=salary_frequency,
            only_with_salary=only_with_salary,
            label=label,
            driver_license_types=driver_license_types,
            accept_temporary=accept_temporary
        )
        return vacancies
    except FileNotFoundError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/apply", response_model=ApplyResponse)
async def apply_to_vacancy(request: ApplyRequest) -> ApplyResponse:
    """
    Отклик на вакансию с опциональным сопроводительным письмом.
    
    Возвращает статус и сообщение результата отклика.
    """
    logger.info(f"Apply request: url={request.url}")
    
    try:
        result = await apply_service.apply(str(request.url), request.message)
        return ApplyResponse(**result)
    except Exception as e:
        logger.error(f"Apply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "session_exists": settings.session_file.exists(),
        "version": "2.0.0"
    }


def run():
    """Запуск сервера."""
    import uvicorn
    
    logger.info(f"Starting HH Automation API on http://{settings.server_host}:{settings.server_port}")
    logger.info("Endpoints:")
    logger.info("  GET  /search?text=Frontend&page=0&work_format=удалённо&experience=нет опыта")
    logger.info("  POST /apply  { 'url': '...', 'message': '...' }")
    logger.info("  GET  /health")
    logger.info("  GET  /docs  (Swagger UI)")
    
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level="info"
    )


if __name__ == "__main__":
    run()
