import shutil
import uuid
from fastapi import FastAPI, Form, File, UploadFile, Request, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, or_
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

UPLOAD_DIRECTORY = "static/uploads/images/"
UPLOAD_FILE_DIRECTORY = "static/uploads/pdf_files"


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


@app.get("/admin_register/", response_class=HTMLResponse)
async def get_admin_register(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if is_admin.user_role == "User":
        return RedirectResponse(url=app.url_path_for("read_root"))

    return templates.TemplateResponse("admin_register.html", {"request": request})


@app.post("/admin_register/")
async def post_admin_register(request: Request, email: str = Form(...), password: str = Form(...),
                              confirm_password: str = Form(...), user_role: str = Form(...),
                              db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if is_admin.user_role == "User":
        return RedirectResponse(url=app.url_path_for("read_root"))

    try:
        if validate_email(email):
            is_user = db.query(db_models.User).filter(db_models.User.email == email).first()
            if not is_user:
                if password == confirm_password:
                    user_data = db_models.User(email=email, password=password, user_role=user_role, user_token=None)
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
async def get_login(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("read_root"))

    is_admin = db.query(db_models.User).filter(db_models.User.user_role == "Admin").first()
    if not is_admin:
        user_data = db_models.User(email="admin123@gmail.com", password="admin123", user_role="Admin", user_token=None)
        db.add(user_data)
        db.commit()
        db.refresh(user_data)

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
    is_token = request.cookies.get('token')
    if is_token:
        error = None
        message = None
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

    return RedirectResponse(url=app.url_path_for("get_login"))


@app.post("/")
async def submit_form(request: Request, numero_tarjeta: int = Form(...), dni: str = Form(...), nombre: str = Form(...),
                      apellidos: str = Form(...), direccion: str = Form(...), fecha_expedicion: str = Form(...),
                      f_nacimiento: str = Form(...), email: str = Form(None), telefono: str = Form(),
                      foto: UploadFile = File(...), fecha_caducidad: str = Form(...),
                      cert_empadronamiento: UploadFile = File(...), cert_ingresos: UploadFile = File(...),
                      acreditacion: UploadFile = File(...), tipo: str = Form(...),
                      db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    is_user = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

    if is_user:
        profile_image_path = None
        if numero_tarjeta or nombre or apellidos or dni or direccion or fecha_expedicion or f_nacimiento or telefono or foto:
            image_id = uuid.uuid4()
            if not os.path.exists(UPLOAD_DIRECTORY):
                os.makedirs(UPLOAD_DIRECTORY)

            if foto:
                profile_image_path = os.path.join(UPLOAD_DIRECTORY, f"{image_id}_{foto.filename}")
                with open(profile_image_path, "wb") as buffer:
                    buffer.write(await foto.read())

            if not os.path.exists(UPLOAD_FILE_DIRECTORY):
                os.makedirs(UPLOAD_FILE_DIRECTORY)

            cert_empadronamiento_path = os.path.join(UPLOAD_FILE_DIRECTORY,
                                                     f"{image_id}_{cert_empadronamiento.filename}")
            cert_ingresos_path = os.path.join(UPLOAD_FILE_DIRECTORY, f"{image_id}_{cert_ingresos.filename}")
            acreditacion_path = os.path.join(UPLOAD_FILE_DIRECTORY, f"{image_id}_{acreditacion.filename}")

            with open(cert_empadronamiento_path, "wb") as f:
                f.write(cert_empadronamiento.file.read())

            with open(cert_ingresos_path, "wb") as f:
                f.write(cert_ingresos.file.read())

            with open(acreditacion_path, "wb") as f:
                f.write(acreditacion.file.read())

            new_record = db_models.Profile(numero_tarjeta=numero_tarjeta, nombre=nombre, apellidos=apellidos,
                                           dni=dni, direccion=direccion, fecha_expedicion=fecha_expedicion,
                                           foto=profile_image_path, f_nacimiento=f_nacimiento, telefono=telefono,
                                           user_id=is_user.id, fecha_caducidad=fecha_caducidad, email=email,
                                           cert_empadronamiento=cert_empadronamiento_path, tipo=tipo,
                                           cert_ingresos=cert_ingresos_path, acreditacion=acreditacion_path)

            db.add(new_record)
            db.commit()
            db.refresh(new_record)

            error = None
            message = "Profile added successfully!"
            return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

        error = "All fields are filled!"
        message = None
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "message": message})

    return RedirectResponse(url=app.url_path_for("get_login"))


@app.get("/show_database/")
async def get_database(request: Request, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    user_data = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    print(user_data.user_role)
    from_data = db.query(db_models.Profile).all()
    return templates.TemplateResponse("database.html", {"request": request, "from_data": from_data,
                                                        "user_data": user_data})


@app.get("/search_user_from/")
async def get_user_from(request: Request, search: str = '', db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    user_data = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    from_data = db.query(db_models.Profile).filter(or_(db_models.Profile.numero_tarjeta.like(f"%{search}%"),
                                                       db_models.Profile.dni.like(f"%{search}%"),
                                                       db_models.Profile.nombre.like(f"%{search}%"),
                                                       db_models.Profile.apellidos.like(f"%{search}%")))
    return templates.TemplateResponse("database.html", {"request": request, "from_data": from_data,
                                                        "user_data": user_data})


@app.get("/edit_form/{from_id}/")
async def edit_form(request: Request, from_id: int, db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    user_data = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    from_data = db.query(db_models.Profile).filter(db_models.Profile.id == from_id).first()
    return templates.TemplateResponse("edit_from.html", {"request": request, "from_data": from_data,
                                                         "user_data": user_data})


@app.post("/update_form/{from_id}/")
async def update_form(request: Request, from_id: int, numero_tarjeta: int = Form(...), dni: str = Form(...), nombre: str = Form(...),
                      apellidos: str = Form(...), direccion: str = Form(...), fecha_expedicion: str = Form(...),
                      f_nacimiento: str = Form(...), email: str = Form(...), telefono: str = Form(),
                      fecha_caducidad: str = Form(...), cert_empadronamiento: UploadFile = File(None),
                      cert_ingresos: UploadFile = File(None), acreditacion: UploadFile = File(None),
                      tipo: str = Form(...), db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if is_admin and is_admin.user_role == "Admin":
        from_data = db.query(db_models.Profile).filter(db_models.Profile.id == from_id).first()
        if from_data:
            from_data.numero_tarjeta = numero_tarjeta
            from_data.dni = dni
            from_data.nombre = nombre
            from_data.apellidos = apellidos
            from_data.direccion = direccion
            from_data.fecha_expedicion = fecha_expedicion
            from_data.f_nacimiento = f_nacimiento
            from_data.email = email
            from_data.telefono = telefono
            from_data.fecha_caducidad = fecha_caducidad
            from_data.tipo = tipo

            upload_directory = UPLOAD_FILE_DIRECTORY

            if cert_empadronamiento and cert_empadronamiento.filename:
                cert_empadronamiento_path = os.path.join(upload_directory, f"{from_id}_{cert_empadronamiento.filename}")
                with open(cert_empadronamiento_path, "wb") as buffer:
                    shutil.copyfileobj(cert_empadronamiento.file, buffer)
                from_data.cert_empadronamiento = cert_empadronamiento_path

            if cert_ingresos and cert_ingresos.filename:
                cert_ingresos_path = os.path.join(upload_directory, f"{from_id}_{cert_ingresos.filename}")
                with open(cert_ingresos_path, "wb") as buffer:
                    shutil.copyfileobj(cert_ingresos.file, buffer)
                from_data.cert_ingresos = cert_ingresos_path

            if acreditacion and acreditacion.filename:
                acreditacion_path = os.path.join(upload_directory, f"{from_id}_{acreditacion.filename}")
                with open(acreditacion_path, "wb") as buffer:
                    shutil.copyfileobj(acreditacion.file, buffer)
                from_data.acreditacion = acreditacion_path

            db.commit()
            db.refresh(from_data)

            message = "Profile updated successfully!"
            return RedirectResponse(url=app.url_path_for("edit_form", from_id=from_id),
                                    status_code=status.HTTP_303_SEE_OTHER)

        error = "Profile not found!"
        return templates.TemplateResponse("edit_from.html", {"request": request, "error": error, "user_data": is_admin})

    return RedirectResponse(url=app.url_path_for("get_login"))


@app.get("/delete_form/{from_id}/")
async def delete_form(request: Request, from_id: int,  db: Session = Depends(get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("get_login"))

    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if is_admin and is_admin.user_role == "Admin":
        from_data = db.query(db_models.Profile).filter(db_models.Profile.id == from_id).first()
        if from_data:
            db.delete(from_data)
            db.commit()
            return RedirectResponse(url=app.url_path_for("get_database"))
        else:
            error = "Profile not found!"
            return templates.TemplateResponse("edit_from.html", {"request": request, "error": error,
                                                                 "user_data": is_admin})

    return RedirectResponse(url=app.url_path_for("get_login"))


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    uvicorn.run("main:app", host='127.0.0.1', port=8000, workers=2, reload=True)
