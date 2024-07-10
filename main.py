from fastapi import FastAPI, Form, File, UploadFile, Request, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_
from sqlalchemy.orm import Session
from db_config.database_config import get_db, Base, engine
from email_validator import validate_email
from models import db_models
import uvicorn
import os

app = FastAPI()
database = []
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIRECTORY = "uploads/"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


@app.get("/register/", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register/")
async def post_register(email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
                        db: Session = Depends(get_db)):
    print(email, password, confirm_password)
    if not validate_email(email):
        is_user = db.query(db_models.User).filter(db_models.User.email == email).first()
        if is_user:
            if password != confirm_password:
                return RedirectResponse(url="/register/", status_code=status.HTTP_303_SEE_OTHER)

            return RedirectResponse(url="/register/", status_code=status.HTTP_303_SEE_OTHER)

    user_data = db_models.User(email=email, password=password)
    db.add(user_data)
    db.commit()
    db.refresh(user_data)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/")
async def post_login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if not validate_email(email):
        is_user = db.query(db_models.User).filter(
            and_(db_models.User.email == email, db_models.User.password == password)).first()
        if not is_user:
            return RedirectResponse(url="/register/", status_code=status.HTTP_303_SEE_OTHER)
        if not is_user.is_active:
            return RedirectResponse(url="/register/", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/user_form/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/user_form/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "records": database})


@app.post("/user_form/")
async def submit_form(id: int = Form(...), numero_tarjeta: int = Form(...), nombre: str = Form(...),
                      apellidos: str = Form(...), dni: str = Form(...), direccion: str = Form(...),
                      fecha_expedicion: str = Form(...), fecha_caducidad: Optional[str] = Form(None),
                      certificado_ingresos: Optional[str] = Form(None), foto: UploadFile = File(None),
                      certificado_jubilacion: Optional[str] = Form(None), db: Session = Depends(get_db)):
    foto_path = None
    if foto:
        foto_path = os.path.join(UPLOAD_DIRECTORY, foto.filename)
        with open(foto_path, "wb") as buffer:
            buffer.write(await foto.read())

    new_record = db_models.Profile(profile_id=id, numero_tarjeta=numero_tarjeta, nombre=nombre, apellidos=apellidos, dni=dni,
                                   direccion=direccion, fecha_expedicion=fecha_expedicion,
                                   fecha_caducidad=fecha_caducidad, foto=foto_path, user_id=1,
                                   certificado_ingresos=certificado_ingresos,
                                   certificado_jubilacion=certificado_jubilacion)

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return RedirectResponse("/user_form/", status_code=status.HTTP_303_SEE_OTHER)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    uvicorn.run("main:app", host='0.0.0.0', port=8000, workers=2, reload=True)
