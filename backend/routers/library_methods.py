from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   Library Method Endpoints
############################################





@router.post("/library/{library_id}/methods/cheapest_book_by/", response_model=None, tags=["Library Methods"])
async def execute_library_cheapest_book_by(
    library_id: int,  # the Library that cheapest_book_by runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Execute the cheapest_book_by method on a Library instance.

    Parameters:
    - author: Author    """
    # Library.cheapest_book_by: load the instance
    _library_object = database.query(Library).filter(Library.id == library_id).first()
    if _library_object is None:
        raise HTTPException(status_code=404, detail="Library not found")
    # Library.cheapest_book_by
    raise HTTPException(
        status_code=501,
        detail="Method 'cheapest_book_by' of Library is modeled but has no implementation - 501, never a fake success",
    )

