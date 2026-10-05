from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()


@router.get("/author/", response_model=None, tags=["Author"])
def get_all_author(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Author)
        author_list = query.all()

        # Serialize with relationships included
        result = []
        for author_item in author_list:
            item_dict = author_item.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            book_list = database.query(Book).join(books_1, Book.id == books_1.c.books).filter(books_1.c.authors == author_item.id).all()
            item_dict['books'] = []
            for book_obj in book_list:
                book_dict = book_obj.__dict__.copy()
                book_dict.pop('_sa_instance_state', None)
                item_dict['books'].append(book_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Author).all()


@router.get("/author/count/", response_model=None, tags=["Author"])
def get_count_author(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Author entities"""
    count = database.query(Author).count()
    return {"count": count}


@router.get("/author/paginated/", response_model=None, tags=["Author"])
def get_paginated_author(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Author entities"""
    total = database.query(Author).count()
    author_list = database.query(Author).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": author_list
        }

    result = []
    for author_item in author_list:
        book_ids = database.query(books_1.c.books).filter(books_1.c.authors == author_item.id).all()
        item_data = {
            "author": author_item,
            "book_ids": [x[0] for x in book_ids],
        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/author/search/", response_model=None, tags=["Author"])
def search_author(
    name: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Author entities by attributes"""
    query = database.query(Author)

    if name is not None:
        query = query.filter(Author.name.ilike(f"%{name}%"))

    results = query.all()
    return results


@router.get("/author/{author_id}/", response_model=None, tags=["Author"])
async def get_author(author_id: int, database: Session = Depends(get_db)) -> Author:
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    book_ids = database.query(books_1.c.books).filter(books_1.c.authors == db_author.id).all()
    response_data = {
        "author": db_author,
        "book_ids": [x[0] for x in book_ids],
}
    return response_data



@router.post("/author/", response_model=None, tags=["Author"])
async def create_author(author_data: AuthorCreate, database: Session = Depends(get_db)) -> Author:

    if author_data.books:
        for id in author_data.books:
            # Entity already validated before creation
            db_book = database.query(Book).filter(Book.id == id).first()
            if not db_book:
                raise HTTPException(status_code=404, detail=f"Book with ID {id} not found")

    db_author = Author(
        birth=author_data.birth,        name=author_data.name        )

    database.add(db_author)
    database.flush()
    database.refresh(db_author)


    if author_data.books:
        for id in author_data.books:
            # Entity already validated before creation
            db_book = database.query(Book).filter(Book.id == id).first()
            # Create the association
            association = books_1.insert().values(authors=db_author.id, books=db_book.id)
            database.execute(association)
            database.flush()


    book_ids = database.query(books_1.c.books).filter(books_1.c.authors == db_author.id).all()
    response_data = {
        "author": db_author,
        "book_ids": [x[0] for x in book_ids],
    }
    database.commit()
    database.refresh(db_author)
    return response_data


@router.post("/author/bulk/", response_model=None, tags=["Author"])
async def bulk_create_author(items: list[AuthorCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Author entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['books']):
        raise HTTPException(status_code=422, detail="Bulk creation of Author with relationships is not supported; use POST /author/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_author = Author(
                birth=item_data.birth,                name=item_data.name            )
            database.add(db_author)
            database.flush()  # Get ID without committing
            created_items.append(db_author.id)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Author entities"
    }


@router.delete("/author/bulk/", response_model=None, tags=["Author"])
async def bulk_delete_author(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Author entities at once"""
    # Aggregate deletion must account for every related lower bound. Until it
    # shares that validation, use the guarded individual delete endpoint.
    if ids:
        raise HTTPException(status_code=409, detail="Bulk deletion of Author can violate required relationships and is not supported; use the individual DELETE /author/ endpoint")
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_author = database.query(Author).filter(Author.id == item_id).first()
        if db_author:
            database.delete(db_author)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Author entities"
    }

@router.put("/author/{author_id}/", response_model=None, tags=["Author"])
async def update_author(author_id: int, author_data: AuthorCreate, database: Session = Depends(get_db)) -> Author:
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    setattr(db_author, 'birth', author_data.birth)
    setattr(db_author, 'name', author_data.name)
    if author_data.books is not None:
        existing_book_ids = [assoc.books for assoc in database.execute(
            books_1.select().where(books_1.c.authors == db_author.id))]

        books_to_remove = set(existing_book_ids) - set(author_data.books)
        for book_id in books_to_remove:
            db_book = database.query(Book).filter(Book.id == book_id).first()
            if db_book is not None and len(db_book.authors) - 1 < 1:
                raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 authors")
            association = books_1.delete().where(
                (books_1.c.authors == db_author.id) & (books_1.c.books == book_id))
            database.execute(association)

        new_book_ids = set(author_data.books) - set(existing_book_ids)
        for book_id in new_book_ids:
            db_book = database.query(Book).filter(Book.id == book_id).first()
            if db_book is None:
                raise HTTPException(status_code=404, detail="Book with ID " + str(book_id) + " not found")
            association = books_1.insert().values(books=db_book.id, authors=db_author.id)
            database.execute(association)
    database.commit()
    database.refresh(db_author)

    book_ids = database.query(books_1.c.books).filter(books_1.c.authors == db_author.id).all()
    response_data = {
        "author": db_author,
        "book_ids": [x[0] for x in book_ids],
    }
    return response_data


@router.delete("/author/{author_id}/", response_model=None, tags=["Author"])
async def delete_author(author_id: int, database: Session = Depends(get_db)):
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    related_books = db_author.books
    for related in (list(related_books) if isinstance(related_books, list) else [item for item in [related_books] if item is not None]):
        remaining = len(related.authors) - 1
        if remaining < 1:
            raise HTTPException(status_code=409, detail="Cannot delete Author " + str(author_id) + ": Book " + str(getattr(related, 'id')) + " requires at least 1 authors")
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_author = {
        attr.key: getattr(db_author, attr.key)
        for attr in db_author.__mapper__.column_attrs
    }
    database.delete(db_author)
    database.commit()
    return deleted_author

@router.post("/author/{author_id}/books/{book_id}/", response_model=None, tags=["Author Relationships"])
async def add_books_to_author(author_id: int, book_id: int, database: Session = Depends(get_db)):
    """Add a Book to this Author's books relationship"""
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if relationship already exists
    existing = database.query(books_1).filter(
        (books_1.c.authors == author_id) &
        (books_1.c.books == book_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = books_1.insert().values(authors=author_id, books=book_id)
    database.execute(association)
    database.commit()

    return {"message": "Book added to books successfully"}


@router.delete("/author/{author_id}/books/{book_id}/", response_model=None, tags=["Author Relationships"])
async def remove_books_from_author(author_id: int, book_id: int, database: Session = Depends(get_db)):
    """Remove a Book from this Author's books relationship"""
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    # Check if relationship exists
    existing = database.query(books_1).filter(
        (books_1.c.authors == author_id) &
        (books_1.c.books == book_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")

    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is not None and len(db_book.authors) - 1 < 1:
        raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 authors")

    # Delete the association
    association = books_1.delete().where(
        (books_1.c.authors == author_id) &
        (books_1.c.books == book_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Book removed from books successfully"}


@router.get("/author/{author_id}/books/", response_model=None, tags=["Author Relationships"])
async def get_books_of_author(author_id: int, database: Session = Depends(get_db)):
    """Get all Book entities related to this Author through books"""
    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    book_ids = database.query(books_1.c.books).filter(books_1.c.authors == author_id).all()
    book_list = database.query(Book).filter(Book.id.in_([id[0] for id in book_ids])).all()

    return {
        "author_id": author_id,
        "books_count": len(book_list),
        "books": book_list
    }



