from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   Book Method Endpoints
############################################





@router.post("/book/{book_id}/methods/decrease_stock/", response_model=None, tags=["Book Methods"])
async def execute_book_decrease_stock(
    book_id: int,  # the Book that decrease_stock runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Execute the decrease_stock method on a Book instance.

    Parameters:
    - qty: int    """
    # Book.decrease_stock: load the instance
    _book_object = database.query(Book).filter(Book.id == book_id).first()
    if _book_object is None:
        raise HTTPException(status_code=404, detail="Book not found")
    # Book.decrease_stock: parameters
    qty = params.get('qty')
    # Book.decrease_stock: execute
    try:
        # Book.decrease_stock: capture stdout to include print outputs in the response
        import io
        import sys
        _decrease_stock_stdout = io.StringIO()
        sys.stdout = _decrease_stock_stdout


        async def wrapper(_book_object):
            """
            Decrease the available stock by the given quantity.

            :param qty: Number of items to remove from stock
            :raises ValueError: If qty is negative or exceeds available stock
            """
            if qty <= 0:
                raise ValueError("Quantity must be a positive integer")

            if qty > _book_object.stock:
                raise ValueError(
                    f"Cannot decrease stock by {qty}. Only {_book_object.stock} items available."
                )

            _book_object.stock -= qty


        result = await wrapper(_book_object)
        # Commit DB
        database.commit()
        database.refresh(_book_object)

        # Restore stdout
        sys.stdout = sys.__stdout__
        output = _decrease_stock_stdout.getvalue()

        return {
            "book_id": book_id,
            "method": "decrease_stock",
            "status": "executed",
            "result": str(result) if result is not None else None,
            "output": output if output else None
        }
    except HTTPException:
        sys.stdout = sys.__stdout__
        raise
    except Exception as e:
        sys.stdout = sys.__stdout__
        raise HTTPException(status_code=500, detail=f"Book.decrease_stock failed: {str(e)}")

