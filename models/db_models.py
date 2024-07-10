from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from db_config.database_config import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    profile = relationship("Profile", back_populates="user")


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, nullable=False)
    numero_tarjeta = Column(Integer, nullable=False)
    nombre = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    dni = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    fecha_expedicion = Column(String, nullable=False)
    fecha_caducidad = Column(String, nullable=False)
    certificado_ingresos = Column(String, nullable=False)
    certificado_jubilacion = Column(String, nullable=False)
    foto = Column(String, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="profile")
