from sqlalchemy.orm import Session
from app.db import crud


def create_profile(db: Session, profile_data):
    return crud.create_profile(db, profile_data)


def list_profiles(db: Session):
    return crud.list_profiles(db)


def get_latest_profile(db: Session):
    return crud.get_latest_profile(db)


def get_profile_by_id(db: Session, profile_id: int):
    return crud.get_profile_by_id(db, profile_id)


def update_profile(db: Session, profile_id: int, profile_data):
    return crud.update_profile(db, profile_id, profile_data)