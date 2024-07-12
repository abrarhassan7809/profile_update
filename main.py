from fastapi import FastAPI, Form, File, UploadFile, Request, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_
from sqlalchemy.orm import Session
from db_config.database_config import get_db, Base, engine
from email_validator import validate_email, EmailNotValidError

from db_config.db_functions import create_token
from models import db_models
import uvicorn
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIRECTORY = "uploads/"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


@app.get("/logout/")
async def logout(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        is_user = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if is_user:
            is_user.user_token = None
            is_user.is_active = False
            db.commit()

        response = RedirectResponse(url=app.url_path_for("get_login"))
        response.delete_cookie('token')
        request.cookies.pop('token')
        return response


@app.get("/register/", response_class=HTMLResponse)
async def get_register(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("read_root"))

    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register/")
async def post_register(request: Request, email: str = Form(...), password: str = Form(...),
                        confirm_password: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("read_root"))

    try:
        if validate_email(email):
            is_user = db.query(db_models.User).filter(db_models.User.email == email).first()
            if not is_user:
                if password == confirm_password:
                    user_data = db_models.User(email=email, password=password, user_token=None)
                    db.add(user_data)
                    db.commit()
                    db.refresh(user_data)
                    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

                else:
                    error = "Password not match!"
                    return templates.TemplateResponse("register.html", {"request": request, "error": error})

            else:
                error = "User Already Exists!"
                return templates.TemplateResponse("register.html", {"request": request, "error": error})

    except EmailNotValidError as e:
        error = "Email not valid!"
        return templates.TemplateResponse("register.html", {"request": request, "error": error})


@app.get("/login/", response_class=HTMLResponse)
async def get_login(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("read_root"))

    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login/")
async def post_login(request: Request, email: str = Form(...), password: str = Form(...),
                     db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("read_root"))

    try:
        if validate_email(email):
            is_user = db.query(db_models.User).filter(
                and_(db_models.User.email == email, db_models.User.password == password)).first()
            if is_user:
                user_token = create_token()
                is_user.user_token = user_token
                is_user.is_active = True
                db.commit()

                response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
                response.set_cookie(key="token", value=user_token)

                return response
            else:
                error = "Invalid Credential!"
                return templates.TemplateResponse("login.html", {"request": request, "error": error})

    except EmailNotValidError as e:
        error = "Invalid Email!"
        return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # is_token = request.cookies.get('token')
    # print('get', is_token)
    # if is_token:
    error = None
    message = None
    return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

    # return RedirectResponse(url=app.url_path_for("get_login"))


@app.post("/")
async def submit_form(request: Request, id: int = Form(...), numero_tarjeta: int = Form(...), nombre: str = Form(...),
                      apellidos: str = Form(...), dni: str = Form(...), direccion: str = Form(...),
                      fecha_expedicion: str = Form(...), fecha_caducidad: str = Form(...),
                      certificado_ingresos: str = Form(), foto: UploadFile = File(None),
                      certificado_jubilacion: str = Form(...), db: Session = Depends(get_db)):
    # is_token = request.cookies.get('token')
    # if not is_token:
    #     return RedirectResponse(url=app.url_path_for("get_login"))
    #
    # is_user = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

    # if is_user:
    foto_path = None
    if id or numero_tarjeta or nombre or apellidos or dni or direccion or fecha_expedicion or fecha_caducidad or certificado_ingresos or foto or certificado_jubilacion:
        if foto:
            foto_path = os.path.join(UPLOAD_DIRECTORY, foto.filename)
            with open(foto_path, "wb") as buffer:
                buffer.write(await foto.read())

        new_record = db_models.Profile(profile_id=id, numero_tarjeta=numero_tarjeta, nombre=nombre, apellidos=apellidos,
                                       dni=dni, direccion=direccion, fecha_expedicion=fecha_expedicion, foto=foto_path,
                                       fecha_caducidad=fecha_caducidad, certificado_ingresos=certificado_ingresos,
                                       user_id=1, certificado_jubilacion=certificado_jubilacion)

        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        error = None
        message = "Profile added successfully!"
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

    error = "All fields are filled!"
    message = None
    return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

    # return RedirectResponse(url=app.url_path_for("get_login"))


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    uvicorn.run("main:app", host='0.0.0.0', port=8000, workers=2, reload=True)
