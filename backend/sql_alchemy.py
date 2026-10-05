import enum
import os
# Both spellings are bound on purpose. Generated code uses the trailing-
# underscore aliases so a modelled class named List, Optional or DateTime
# cannot shadow them. The PLAIN names are imported too because this file is
# routinely edited afterwards by an LLM, which writes ordinary Python and has
# no reason to know about the aliasing convention; without the plain names
# such edits fail to import:
#
#     Mapped_[Optional[int]]        undefined name 'Optional'
#     mapped_column(DateTime())     undefined name 'DateTime'
#
# so every aliased name below is bound both ways.
from typing import List, Optional, List as List_, Optional as Optional_
from sqlalchemy import (
    create_engine, Enum, UniqueConstraint as _UniqueConstraint, event as _sa_event,
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Interval,
    PickleType, String, Table, Text, Time,
    Column as Column_, ForeignKey as ForeignKey_, Table as Table_,
    Text as Text_, Boolean as Boolean_, String as String_, Date as Date_,
    Time as Time_, DateTime as DateTime_, Float as Float_, Integer as Integer_,
    Interval as Interval_, PickleType as PickleType_,
)
from sqlalchemy.orm import (
    column_property, DeclarativeBase, Mapped, Mapped as Mapped_, mapped_column,
    relationship
)
from datetime import datetime as dt_datetime, time as dt_time, date as dt_date, timedelta as dt_timedelta
from uuid import uuid4 as _uuid4


def _new_str_id() -> str:
    """Server-side surrogate for string primary keys named ``id``.

    A string PK has no autoincrement; without a default every INSERT dies
    on NOT NULL (the id is in nobody's hands: create schemas rightly
    exclude the server-owned ``id``, so the server must mint it).
    """
    return _uuid4().hex


def _configure_sqlite_engine(engine):
    """Enforce declared foreign keys on every SQLite connection."""
    if engine.dialect.name == "sqlite":
        @_sa_event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            previous_autocommit = getattr(connection, "autocommit", None)
            if previous_autocommit is not None:
                connection.autocommit = True
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
                if previous_autocommit is not None:
                    connection.autocommit = previous_autocommit


class Base(DeclarativeBase):
    pass

# Definitions of Enumerations
class Genre(enum.Enum):
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


# Tables definition for many-to-many relationships
books = Table_(
    "books",
    Base.metadata,
    Column_("books", ForeignKey_("book.id"), primary_key=True),
    Column_("library", ForeignKey_("library.id"), primary_key=True),
)
books_1 = Table_(
    "books_1",
    Base.metadata,
    Column_("authors", ForeignKey_("author.id"), primary_key=True),
    Column_("books", ForeignKey_("book.id"), primary_key=True),
)

# Tables definition
class Library(Base):
    __tablename__ = "library"
    id: Mapped_[int] = mapped_column(primary_key=True)
    name: Mapped_[str] = mapped_column(String_(100))
    web_page: Mapped_[str] = mapped_column(String_(100))
    address: Mapped_[str] = mapped_column(String_(100))
    telephone: Mapped_[str] = mapped_column(String_(100))

class Book(Base):
    __tablename__ = "book"
    id: Mapped_[int] = mapped_column(primary_key=True)
    title: Mapped_[str] = mapped_column(String_(100))
    pages: Mapped_[int] = mapped_column(Integer_)
    stock: Mapped_[int] = mapped_column(Integer_)
    price: Mapped_[float] = mapped_column(Float_)
    release: Mapped_[dt_date] = mapped_column(Date_)
    genre: Mapped_[Genre] = mapped_column(Enum(Genre))

    def decrease_stock(self, qty: int):
        """
        Decrease the available stock by the given quantity.

        :param qty: Number of items to remove from stock
        :raises ValueError: If qty is negative or exceeds available stock
        """
        if qty <= 0:
            raise ValueError("Quantity must be a positive integer")

        if qty > self.stock:
            raise ValueError(
                f"Cannot decrease stock by {qty}. Only {self.stock} items available."
            )

        self.stock -= qty


class Author(Base):
    __tablename__ = "author"
    id: Mapped_[int] = mapped_column(primary_key=True)
    name: Mapped_[str] = mapped_column(String_(100))
    birth: Mapped_[dt_date] = mapped_column(Date_)


#--- Relationships of the library table
Library.books: Mapped_[List_["Book"]] = relationship("Book", secondary=books, back_populates="library")

#--- Relationships of the book table
Book.authors: Mapped_[List_["Author"]] = relationship("Author", secondary=books_1, back_populates="books")
Book.library: Mapped_[List_["Library"]] = relationship("Library", secondary=books, back_populates="books")

#--- Relationships of the author table
Author.books: Mapped_[List_["Book"]] = relationship("Book", secondary=books_1, back_populates="authors")

# Database connection (override the default with the DATABASE_URL environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/Library.db")  # SQLite connection
engine = create_engine(DATABASE_URL)
_configure_sqlite_engine(engine)

if __name__ == "__main__":
    # Create tables in the database only when this module is executed directly,
    # so importing it never touches the database as a side effect.
    if DATABASE_URL.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)  # folder for the default SQLite database
    Base.metadata.create_all(engine, checkfirst=True)