from sqlalchemy.orm import Session
from app.db import crud


def create_review(db: Session, review_data):
    return crud.create_review(db, review_data)


def get_reviews_for_profile(db: Session, profile_id: int):
    return crud.get_reviews_for_profile(db, profile_id)


def get_reviews_by_disposition(db: Session, profile_id: int, disposition: str):
    return crud.get_reviews_by_disposition(db, profile_id, disposition)