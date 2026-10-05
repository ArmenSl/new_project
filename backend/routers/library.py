from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()


@router.get("/library/", response_model=None, tags=["Library"])
def get_all_library(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Library)
        library_list = query.all()

        # Serialize with relationships included
        result = []
        for library_item in library_list:
            item_dict = library_item.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            book_list = database.query(Book).join(books, Book.id == books.c.books).filter(books.c.library == library_item.id).all()
            item_dict['books'] = []
            for book_obj in book_list:
                book_dict = book_obj.__dict__.copy()
                book_dict.pop('_sa_instance_state', None)
                item_dict['books'].append(book_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Library).all()


@router.get("/library/count/", response_model=None, tags=["Library"])
def get_count_library(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Library entities"""
    count = database.query(Library).count()
    return {"count": count}


@router.get("/library/paginated/", response_model=None, tags=["Library"])
def get_paginated_library(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Library entities"""
    total = database.query(Library).count()
    library_list = database.query(Library).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": library_list
        }

    result = []
    for library_item in library_list:
        book_ids = database.query(books.c.books).filter(books.c.library == library_item.id).all()
        item_data = {
            "library": library_item,
            "book_ids": [x[0] for x in book_ids],
        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/library/search/", response_model=None, tags=["Library"])
def search_library(
    address: str = None,
    name: str = None,
    telephone: str = None,
    web_page: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Library entities by attributes"""
    query = database.query(Library)

    if address is not None:
        query = query.filter(Library.address.ilike(f"%{address}%"))
    if name is not None:
        query = query.filter(Library.name.ilike(f"%{name}%"))
    if telephone is not None:
        query = query.filter(Library.telephone.ilike(f"%{telephone}%"))
    if web_page is not None:
        query = query.filter(Library.web_page.ilike(f"%{web_page}%"))

    results = query.all()
    return results


@router.get("/library/{library_id}/", response_model=None, tags=["Library"])
async def get_library(library_id: int, database: Session = Depends(get_db)) -> Library:
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    book_ids = database.query(books.c.books).filter(books.c.library == db_library.id).all()
    response_data = {
        "library": db_library,
        "book_ids": [x[0] for x in book_ids],
}
    return response_data



@router.post("/library/", response_model=None, tags=["Library"])
async def create_library(library_data: LibraryCreate, database: Session = Depends(get_db)) -> Library:

    if library_data.books:
        for id in library_data.books:
            # Entity already validated before creation
            db_book = database.query(Book).filter(Book.id == id).first()
            if not db_book:
                raise HTTPException(status_code=404, detail=f"Book with ID {id} not found")

    db_library = Library(
        address=library_data.address,        name=library_data.name,        telephone=library_data.telephone,        web_page=library_data.web_page        )

    database.add(db_library)
    database.flush()
    database.refresh(db_library)


    if library_data.books:
        for id in library_data.books:
            # Entity already validated before creation
            db_book = database.query(Book).filter(Book.id == id).first()
            # Create the association
            association = books.insert().values(library=db_library.id, books=db_book.id)
            database.execute(association)
            database.flush()


    book_ids = database.query(books.c.books).filter(books.c.library == db_library.id).all()
    response_data = {
        "library": db_library,
        "book_ids": [x[0] for x in book_ids],
    }
    database.commit()
    database.refresh(db_library)
    return response_data


@router.post("/library/bulk/", response_model=None, tags=["Library"])
async def bulk_create_library(items: list[LibraryCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Library entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['books']):
        raise HTTPException(status_code=422, detail="Bulk creation of Library with relationships is not supported; use POST /library/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_library = Library(
                address=item_data.address,                name=item_data.name,                telephone=item_data.telephone,                web_page=item_data.web_page            )
            database.add(db_library)
            database.flush()  # Get ID without committing
            created_items.append(db_library.id)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Library entities"
    }


@router.delete("/library/bulk/", response_model=None, tags=["Library"])
async def bulk_delete_library(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Library entities at once"""
    # Aggregate deletion must account for every related lower bound. Until it
    # shares that validation, use the guarded individual delete endpoint.
    if ids:
        raise HTTPException(status_code=409, detail="Bulk deletion of Library can violate required relationships and is not supported; use the individual DELETE /library/ endpoint")
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_library = database.query(Library).filter(Library.id == item_id).first()
        if db_library:
            database.delete(db_library)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Library entities"
    }

@router.put("/library/{library_id}/", response_model=None, tags=["Library"])
async def update_library(library_id: int, library_data: LibraryCreate, database: Session = Depends(get_db)) -> Library:
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    setattr(db_library, 'address', library_data.address)
    setattr(db_library, 'name', library_data.name)
    setattr(db_library, 'telephone', library_data.telephone)
    setattr(db_library, 'web_page', library_data.web_page)
    if library_data.books is not None:
        existing_book_ids = [assoc.books for assoc in database.execute(
            books.select().where(books.c.library == db_library.id))]

        books_to_remove = set(existing_book_ids) - set(library_data.books)
        for book_id in books_to_remove:
            db_book = database.query(Book).filter(Book.id == book_id).first()
            if db_book is not None and len(db_book.library) - 1 < 1:
                raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 library")
            association = books.delete().where(
                (books.c.library == db_library.id) & (books.c.books == book_id))
            database.execute(association)

        new_book_ids = set(library_data.books) - set(existing_book_ids)
        for book_id in new_book_ids:
            db_book = database.query(Book).filter(Book.id == book_id).first()
            if db_book is None:
                raise HTTPException(status_code=404, detail="Book with ID " + str(book_id) + " not found")
            association = books.insert().values(books=db_book.id, library=db_library.id)
            database.execute(association)
    database.commit()
    database.refresh(db_library)

    book_ids = database.query(books.c.books).filter(books.c.library == db_library.id).all()
    response_data = {
        "library": db_library,
        "book_ids": [x[0] for x in book_ids],
    }
    return response_data


@router.delete("/library/{library_id}/", response_model=None, tags=["Library"])
async def delete_library(library_id: int, database: Session = Depends(get_db)):
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")
    related_books = db_library.books
    for related in (list(related_books) if isinstance(related_books, list) else [item for item in [related_books] if item is not None]):
        remaining = len(related.library) - 1
        if remaining < 1:
            raise HTTPException(status_code=409, detail="Cannot delete Library " + str(library_id) + ": Book " + str(getattr(related, 'id')) + " requires at least 1 library")
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_library = {
        attr.key: getattr(db_library, attr.key)
        for attr in db_library.__mapper__.column_attrs
    }
    database.delete(db_library)
    database.commit()
    return deleted_library

@router.post("/library/{library_id}/books/{book_id}/", response_model=None, tags=["Library Relationships"])
async def add_books_to_library(library_id: int, book_id: int, database: Session = Depends(get_db)):
    """Add a Book to this Library's books relationship"""
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if relationship already exists
    existing = database.query(books).filter(
        (books.c.library == library_id) &
        (books.c.books == book_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = books.insert().values(library=library_id, books=book_id)
    database.execute(association)
    database.commit()

    return {"message": "Book added to books successfully"}


@router.delete("/library/{library_id}/books/{book_id}/", response_model=None, tags=["Library Relationships"])
async def remove_books_from_library(library_id: int, book_id: int, database: Session = Depends(get_db)):
    """Remove a Book from this Library's books relationship"""
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    # Check if relationship exists
    existing = database.query(books).filter(
        (books.c.library == library_id) &
        (books.c.books == book_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")

    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is not None and len(db_book.library) - 1 < 1:
        raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 library")

    # Delete the association
    association = books.delete().where(
        (books.c.library == library_id) &
        (books.c.books == book_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Book removed from books successfully"}


@router.get("/library/{library_id}/books/", response_model=None, tags=["Library Relationships"])
async def get_books_of_library(library_id: int, database: Session = Depends(get_db)):
    """Get all Book entities related to this Library through books"""
    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    book_ids = database.query(books.c.books).filter(books.c.library == library_id).all()
    book_list = database.query(Book).filter(Book.id.in_([id[0] for id in book_ids])).all()

    return {
        "library_id": library_id,
        "books_count": len(book_list),
        "books": book_list
    }



