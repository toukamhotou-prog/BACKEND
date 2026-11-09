from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

SQLALCHEMY_DATABASE_URL= os.environ.get(
    "DATABASE_URL",
    "postgresql://epreuvespro_db_user:Zoi07uVhyokYu9cuLAYCYDgSAGl7UTWB@dpg-dbp5f60n74is73cttfh0-a/epreuvespro_db"
    )
engine = create_engine(SQLALCHEMY_DATABASE_URL)
sessionLocal= sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base= declarative_base()

def get_db():
    db=sessionLocal()
    try:
        yield db
    finally:
        db.close()