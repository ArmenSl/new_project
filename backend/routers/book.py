from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()


@router.get("/book/", response_model=None, tags=["Book"])
def get_all_book(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Book)
        book_list = query.all()

        # Serialize with relationships included
        result = []
        for book_item in book_list:
            item_dict = book_item.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            library_list = database.query(Library).join(books, Library.id == books.c.library).filter(books.c.books == book_item.id).all()
            item_dict['library'] = []
            for library_obj in library_list:
                library_dict = library_obj.__dict__.copy()
                library_dict.pop('_sa_instance_state', None)
                item_dict['library'].append(library_dict)
            author_list = database.query(Author).join(books_1, Author.id == books_1.c.authors).filter(books_1.c.books == book_item.id).all()
            item_dict['authors'] = []
            for author_obj in author_list:
                author_dict = author_obj.__dict__.copy()
                author_dict.pop('_sa_instance_state', None)
                item_dict['authors'].append(author_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Book).all()


@router.get("/book/count/", response_model=None, tags=["Book"])
def get_count_book(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Book entities"""
    count = database.query(Book).count()
    return {"count": count}


@router.get("/book/paginated/", response_model=None, tags=["Book"])
def get_paginated_book(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Book entities"""
    total = database.query(Book).count()
    book_list = database.query(Book).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": book_list
        }

    result = []
    for book_item in book_list:
        library_ids = database.query(books.c.library).filter(books.c.books == book_item.id).all()
        author_ids = database.query(books_1.c.authors).filter(books_1.c.books == book_item.id).all()
        item_data = {
            "book": book_item,
            "library_ids": [x[0] for x in library_ids],
            "author_ids": [x[0] for x in author_ids],
        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/book/search/", response_model=None, tags=["Book"])
def search_book(
    pages: int = None,
    price: float = None,
    stock: int = None,
    title: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Book entities by attributes"""
    query = database.query(Book)

    if pages is not None:
        query = query.filter(Book.pages == pages)
    if price is not None:
        query = query.filter(Book.price == price)
    if stock is not None:
        query = query.filter(Book.stock == stock)
    if title is not None:
        query = query.filter(Book.title.ilike(f"%{title}%"))

    results = query.all()
    return results


@router.get("/book/{book_id}/", response_model=None, tags=["Book"])
async def get_book(book_id: int, database: Session = Depends(get_db)) -> Book:
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    library_ids = database.query(books.c.library).filter(books.c.books == db_book.id).all()
    author_ids = database.query(books_1.c.authors).filter(books_1.c.books == db_book.id).all()
    response_data = {
        "book": db_book,
        "library_ids": [x[0] for x in library_ids],
        "author_ids": [x[0] for x in author_ids],
}
    return response_data



@router.post("/book/", response_model=None, tags=["Book"])
async def create_book(book_data: BookCreate, database: Session = Depends(get_db)) -> Book:

    if not book_data.library or len(book_data.library) < 1:
        raise HTTPException(status_code=400, detail="At least 1 Library(s) required")
    if book_data.library:
        for id in book_data.library:
            # Entity already validated before creation
            db_library = database.query(Library).filter(Library.id == id).first()
            if not db_library:
                raise HTTPException(status_code=404, detail=f"Library with ID {id} not found")
    if not book_data.authors or len(book_data.authors) < 1:
        raise HTTPException(status_code=400, detail="At least 1 Author(s) required")
    if book_data.authors:
        for id in book_data.authors:
            # Entity already validated before creation
            db_author = database.query(Author).filter(Author.id == id).first()
            if not db_author:
                raise HTTPException(status_code=404, detail=f"Author with ID {id} not found")

    db_book = Book(
        genre=book_data.genre.name,        pages=book_data.pages,        price=book_data.price,        release=book_data.release,        stock=book_data.stock,        title=book_data.title        )

    database.add(db_book)
    database.flush()
    database.refresh(db_book)


    if book_data.library:
        for id in book_data.library:
            # Entity already validated before creation
            db_library = database.query(Library).filter(Library.id == id).first()
            # Create the association
            association = books.insert().values(books=db_book.id, library=db_library.id)
            database.execute(association)
            database.flush()
    if book_data.authors:
        for id in book_data.authors:
            # Entity already validated before creation
            db_author = database.query(Author).filter(Author.id == id).first()
            # Create the association
            association = books_1.insert().values(books=db_book.id, authors=db_author.id)
            database.execute(association)
            database.flush()


    library_ids = database.query(books.c.library).filter(books.c.books == db_book.id).all()
    author_ids = database.query(books_1.c.authors).filter(books_1.c.books == db_book.id).all()
    response_data = {
        "book": db_book,
        "library_ids": [x[0] for x in library_ids],
        "author_ids": [x[0] for x in author_ids],
    }
    database.commit()
    database.refresh(db_book)
    return response_data


@router.post("/book/bulk/", response_model=None, tags=["Book"])
async def bulk_create_book(items: list[BookCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Book entities at once"""
    if items:
        raise HTTPException(status_code=422, detail="Bulk creation of Book with required relationships is not supported; use POST /book/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_book = Book(
                genre=item_data.genre.name,                pages=item_data.pages,                price=item_data.price,                release=item_data.release,                stock=item_data.stock,                title=item_data.title            )
            database.add(db_book)
            database.flush()  # Get ID without committing
            created_items.append(db_book.id)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Book entities"
    }


@router.delete("/book/bulk/", response_model=None, tags=["Book"])
async def bulk_delete_book(ids: list[int], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Book entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_book = database.query(Book).filter(Book.id == item_id).first()
        if db_book:
            database.delete(db_book)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Book entities"
    }

@router.put("/book/{book_id}/", response_model=None, tags=["Book"])
async def update_book(book_id: int, book_data: BookCreate, database: Session = Depends(get_db)) -> Book:
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    setattr(db_book, 'genre', book_data.genre.name)
    setattr(db_book, 'pages', book_data.pages)
    setattr(db_book, 'price', book_data.price)
    setattr(db_book, 'release', book_data.release)
    setattr(db_book, 'stock', book_data.stock)
    setattr(db_book, 'title', book_data.title)
    if book_data.library is not None:
        if len(book_data.library) < 1:
            raise HTTPException(status_code=400, detail="At least 1 Library(s) required")
        existing_library_ids = [assoc.library for assoc in database.execute(
            books.select().where(books.c.books == db_book.id))]

        librarys_to_remove = set(existing_library_ids) - set(book_data.library)
        for library_id in librarys_to_remove:
            association = books.delete().where(
                (books.c.books == db_book.id) & (books.c.library == library_id))
            database.execute(association)

        new_library_ids = set(book_data.library) - set(existing_library_ids)
        for library_id in new_library_ids:
            db_library = database.query(Library).filter(Library.id == library_id).first()
            if db_library is None:
                raise HTTPException(status_code=404, detail="Library with ID " + str(library_id) + " not found")
            association = books.insert().values(library=db_library.id, books=db_book.id)
            database.execute(association)
    if book_data.authors is not None:
        if len(book_data.authors) < 1:
            raise HTTPException(status_code=400, detail="At least 1 Author(s) required")
        existing_author_ids = [assoc.authors for assoc in database.execute(
            books_1.select().where(books_1.c.books == db_book.id))]

        authors_to_remove = set(existing_author_ids) - set(book_data.authors)
        for author_id in authors_to_remove:
            association = books_1.delete().where(
                (books_1.c.books == db_book.id) & (books_1.c.authors == author_id))
            database.execute(association)

        new_author_ids = set(book_data.authors) - set(existing_author_ids)
        for author_id in new_author_ids:
            db_author = database.query(Author).filter(Author.id == author_id).first()
            if db_author is None:
                raise HTTPException(status_code=404, detail="Author with ID " + str(author_id) + " not found")
            association = books_1.insert().values(authors=db_author.id, books=db_book.id)
            database.execute(association)
    database.commit()
    database.refresh(db_book)

    library_ids = database.query(books.c.library).filter(books.c.books == db_book.id).all()
    author_ids = database.query(books_1.c.authors).filter(books_1.c.books == db_book.id).all()
    response_data = {
        "book": db_book,
        "library_ids": [x[0] for x in library_ids],
        "author_ids": [x[0] for x in author_ids],
    }
    return response_data


@router.delete("/book/{book_id}/", response_model=None, tags=["Book"])
async def delete_book(book_id: int, database: Session = Depends(get_db)):
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_book = {
        attr.key: getattr(db_book, attr.key)
        for attr in db_book.__mapper__.column_attrs
    }
    database.delete(db_book)
    database.commit()
    return deleted_book

@router.post("/book/{book_id}/library/{library_id}/", response_model=None, tags=["Book Relationships"])
async def add_library_to_book(book_id: int, library_id: int, database: Session = Depends(get_db)):
    """Add a Library to this Book's library relationship"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    db_library = database.query(Library).filter(Library.id == library_id).first()
    if db_library is None:
        raise HTTPException(status_code=404, detail="Library not found")

    # Check if relationship already exists
    existing = database.query(books).filter(
        (books.c.books == book_id) &
        (books.c.library == library_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = books.insert().values(books=book_id, library=library_id)
    database.execute(association)
    database.commit()

    return {"message": "Library added to library successfully"}


@router.delete("/book/{book_id}/library/{library_id}/", response_model=None, tags=["Book Relationships"])
async def remove_library_from_book(book_id: int, library_id: int, database: Session = Depends(get_db)):
    """Remove a Library from this Book's library relationship"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if relationship exists
    existing = database.query(books).filter(
        (books.c.books == book_id) &
        (books.c.library == library_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")

    if len(db_book.library) - 1 < 1:
        raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 library")

    # Delete the association
    association = books.delete().where(
        (books.c.books == book_id) &
        (books.c.library == library_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Library removed from library successfully"}


@router.get("/book/{book_id}/library/", response_model=None, tags=["Book Relationships"])
async def get_library_of_book(book_id: int, database: Session = Depends(get_db)):
    """Get all Library entities related to this Book through library"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    library_ids = database.query(books.c.library).filter(books.c.books == book_id).all()
    library_list = database.query(Library).filter(Library.id.in_([id[0] for id in library_ids])).all()

    return {
        "book_id": book_id,
        "library_count": len(library_list),
        "library": library_list
    }

@router.post("/book/{book_id}/authors/{author_id}/", response_model=None, tags=["Book Relationships"])
async def add_authors_to_book(book_id: int, author_id: int, database: Session = Depends(get_db)):
    """Add a Author to this Book's authors relationship"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    db_author = database.query(Author).filter(Author.id == author_id).first()
    if db_author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    # Check if relationship already exists
    existing = database.query(books_1).filter(
        (books_1.c.books == book_id) &
        (books_1.c.authors == author_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")

    # Create the association
    association = books_1.insert().values(books=book_id, authors=author_id)
    database.execute(association)
    database.commit()

    return {"message": "Author added to authors successfully"}


@router.delete("/book/{book_id}/authors/{author_id}/", response_model=None, tags=["Book Relationships"])
async def remove_authors_from_book(book_id: int, author_id: int, database: Session = Depends(get_db)):
    """Remove a Author from this Book's authors relationship"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if relationship exists
    existing = database.query(books_1).filter(
        (books_1.c.books == book_id) &
        (books_1.c.authors == author_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")

    if len(db_book.authors) - 1 < 1:
        raise HTTPException(status_code=409, detail="Book " + str(book_id) + " requires at least 1 authors")

    # Delete the association
    association = books_1.delete().where(
        (books_1.c.books == book_id) &
        (books_1.c.authors == author_id)
    )
    database.execute(association)
    database.commit()

    return {"message": "Author removed from authors successfully"}


@router.get("/book/{book_id}/authors/", response_model=None, tags=["Book Relationships"])
async def get_authors_of_book(book_id: int, database: Session = Depends(get_db)):
    """Get all Author entities related to this Book through authors"""
    db_book = database.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    author_ids = database.query(books_1.c.authors).filter(books_1.c.books == book_id).all()
    author_list = database.query(Author).filter(Author.id.in_([id[0] for id in author_ids])).all()

    return {
        "book_id": book_id,
        "authors_count": len(author_list),
        "authors": author_list
    }



