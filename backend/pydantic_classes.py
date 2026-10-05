from datetime import datetime, date, time
from typing import Any, List, Optional, Union, Set
from enum import Enum
from pydantic import BaseModel, field_validator


############################################
# Enumerations are defined here
############################################

class Genre(Enum):
    Poetry = "Poetry"
    Thriller = "Thriller"
    History = "History"
    Technology = "Technology"
    Romance = "Romance"
    Horror = "Horror"
    Adventure = "Adventure"
    Philosophy = "Philosophy"
    Cookbooks = "Cookbooks"
    Fantasy = "Fantasy"

############################################
# Classes are defined here
############################################
class LibraryCreate(BaseModel):
    address: str
    name: str
    telephone: str
    web_page: str
    books: Optional[List[int]] = None  # N:M Relationship (optional)


class BookCreate(BaseModel):
    genre: Genre
    pages: int
    price: float
    release: date
    stock: int
    title: str
    library: List[int]  # N:M Relationship
    authors: List[int]  # N:M Relationship

    @field_validator('pages')
    @classmethod
    def validate_pages_1(cls, v):
        """OCL Constraint: inv1"""
        if not (v > 10):
            raise ValueError('pages must be > 10')
        return v

class AuthorCreate(BaseModel):
    birth: date
    name: str
    books: Optional[List[int]] = None  # N:M Relationship (optional)


