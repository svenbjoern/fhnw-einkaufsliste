from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import business
from app.database import datenbank_initialisieren, engine
from app.services import router

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    datenbank_initialisieren(engine)
    yield


app = FastAPI(title="Digitale Einkaufsliste", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(business.UngueltigeDaten)
async def ungueltige_daten(request: Request, error: business.UngueltigeDaten):
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(business.NichtGefunden)
async def nicht_gefunden(request: Request, error: business.NichtGefunden):
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(RequestValidationError)
async def falsches_format(request: Request, error: RequestValidationError):
    feld = error.errors()[0]["loc"][-1]
    meldung = "Ungültige Eingabe. Bitte Pflichtfelder und Datentypen prüfen."
    if feld == "name":
        meldung = "Bitte gib einen Namen ein."
    if feld in ("menge", "zusaetzliche_menge"):
        meldung = "Die Menge muss grösser als null sein und darf höchstens drei Nachkommastellen haben."
    return JSONResponse(status_code=422, content={"detail": meldung})


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
