import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "mysql+pymysql://clubcore:clubcore@db:3306/clubcore"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
