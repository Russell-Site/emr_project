from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.models import (
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
    User
)
from websocket_manager import manager


router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


# ============================================================
# GET ALL INVENTORY ITEMS
# ============================================================

@router.get("")
def get_inventory(db: Session = Depends(get_db)):

    items = (
        db.query(InventoryItem)
        .filter(InventoryItem.is_active == True)
        .order_by(InventoryItem.item_name.asc())
        .all()
    )

    result = []

    for item in items:

        stock = (
            db.query(InventoryStock)
            .filter(
                InventoryStock.item_id == item.item_id
            )
            .first()
        )

        quantity = stock.quantity if stock else 0

        result.append({
            "item_id": item.item_id,
            "item_name": item.item_name,
            "category": item.category,
            "description": item.description,
            "unit": item.unit,
            "reorder_level": item.reorder_level,
            "quantity": quantity,
            "is_active": item.is_active,
            "low_stock": (
                quantity > 0
                and quantity <= item.reorder_level
            ),
            "out_of_stock": quantity == 0,
            "created_at": item.created_at,
            "updated_at": item.updated_at
        })

    return result


# ============================================================
# GET SINGLE INVENTORY ITEM
# ============================================================

@router.get("/{item_id}")
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.item_id == item_id
        )
        .first()
    )

    quantity = stock.quantity if stock else 0

    return {
        "item_id": item.item_id,
        "item_name": item.item_name,
        "category": item.category,
        "description": item.description,
        "unit": item.unit,
        "reorder_level": item.reorder_level,
        "quantity": quantity,
        "is_active": item.is_active
    }


# ============================================================
# CREATE INVENTORY ITEM
# ============================================================

@router.post("")
async def create_inventory_item(
    data: dict,
    db: Session = Depends(get_db)
):

    item_name = str(
        data.get("item_name", "")
    ).strip()

    category = data.get("category")
    unit = str(
        data.get("unit", "")
    ).strip()

    description = data.get("description")

    reorder_level = int(
        data.get("reorder_level", 10)
    )

    quantity = int(
        data.get("quantity", 0)
    )

    user_id = data.get("user_id")

    if not item_name:
        raise HTTPException(
            status_code=400,
            detail="Item name is required."
        )

    if category not in [
        "Medicine",
        "Vaccine",
        "Medical Supply"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid inventory category."
        )

    if not unit:
        raise HTTPException(
            status_code=400,
            detail="Unit is required."
        )

    if reorder_level < 0:
        raise HTTPException(
            status_code=400,
            detail="Reorder level cannot be negative."
        )

    if quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative."
        )

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID is required."
        )

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid user."
        )

    existing = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_name == item_name,
            InventoryItem.is_active == True
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An inventory item with this name already exists."
        )

    item = InventoryItem(
        item_name=item_name,
        category=category,
        description=description,
        unit=unit,
        reorder_level=reorder_level,
        is_active=True
    )

    db.add(item)
    db.flush()

    stock = InventoryStock(
        item_id=item.item_id,
        quantity=quantity
    )

    db.add(stock)

    transaction = InventoryTransaction(
        item_id=item.item_id,
        transaction_type="Stock In",
        quantity=quantity,
        previous_stock=0,
        new_stock=quantity,
        remarks="Initial stock",
        user_id=user_id
    )

    db.add(transaction)

    db.commit()
    db.refresh(item)

    await manager.broadcast({
        "type": "inventory_created",
        "item_id": item.item_id,
        "item_name": item.item_name
    })

    return {
        "message": "Inventory item created successfully.",
        "item_id": item.item_id
    }


# ============================================================
# UPDATE INVENTORY ITEM
# ============================================================

@router.put("/{item_id}")
async def update_inventory_item(
    item_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID is required."
        )

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid user."
        )

    item_name = str(
        data.get("item_name", "")
    ).strip()

    category = data.get("category")

    unit = str(
        data.get("unit", "")
    ).strip()

    description = data.get("description")

    reorder_level = int(
        data.get("reorder_level", 10)
    )

    if not item_name:
        raise HTTPException(
            status_code=400,
            detail="Item name is required."
        )

    if category not in [
        "Medicine",
        "Vaccine",
        "Medical Supply"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid inventory category."
        )

    if not unit:
        raise HTTPException(
            status_code=400,
            detail="Unit is required."
        )

    if reorder_level < 0:
        raise HTTPException(
            status_code=400,
            detail="Reorder level cannot be negative."
        )

    duplicate = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_name == item_name,
            InventoryItem.item_id != item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=400,
            detail="Another inventory item already uses this name."
        )

    item.item_name = item_name
    item.category = category
    item.unit = unit
    item.description = description
    item.reorder_level = reorder_level

    db.commit()
    db.refresh(item)

    await manager.broadcast({
        "type": "inventory_updated",
        "item_id": item.item_id,
        "item_name": item.item_name
    })

    return {
        "message": "Inventory item updated successfully."
    }


# ============================================================
# DELETE / DEACTIVATE INVENTORY ITEM
# ============================================================

@router.delete("/{item_id}")
async def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    item.is_active = False

    db.commit()

    await manager.broadcast({
        "type": "inventory_deleted",
        "item_id": item_id
    })

    return {
        "message": "Inventory item deleted successfully."
    }


# ============================================================
# STOCK IN
# ============================================================

@router.post("/{item_id}/stock-in")
async def stock_in(
    item_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    quantity = int(
        data.get("quantity", 0)
    )

    remarks = data.get("remarks")
    user_id = data.get("user_id")

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0."
        )

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid user."
        )

    stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.item_id == item_id
        )
        .first()
    )

    if not stock:
        stock = InventoryStock(
            item_id=item_id,
            quantity=0
        )
        db.add(stock)
        db.flush()

    previous_stock = stock.quantity
    new_stock = previous_stock + quantity

    stock.quantity = new_stock

    transaction = InventoryTransaction(
        item_id=item_id,
        transaction_type="Stock In",
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        remarks=remarks,
        user_id=user_id
    )

    db.add(transaction)

    db.commit()

    await manager.broadcast({
        "type": "inventory_stock_updated",
        "item_id": item_id,
        "item_name": item.item_name,
        "transaction_type": "Stock In",
        "quantity": quantity,
        "previous_stock": previous_stock,
        "new_stock": new_stock
    })

    return {
        "message": "Stock added successfully.",
        "new_stock": new_stock
    }


# ============================================================
# STOCK OUT
# ============================================================

@router.post("/{item_id}/stock-out")
async def stock_out(
    item_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id,
            InventoryItem.is_active == True
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    quantity = int(
        data.get("quantity", 0)
    )

    remarks = data.get("remarks")
    user_id = data.get("user_id")

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0."
        )

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid user."
        )

    stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.item_id == item_id
        )
        .first()
    )

    if not stock:
        raise HTTPException(
            status_code=400,
            detail="Stock record not found."
        )

    previous_stock = stock.quantity

    if quantity > previous_stock:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock available."
        )

    new_stock = previous_stock - quantity

    stock.quantity = new_stock

    transaction = InventoryTransaction(
        item_id=item_id,
        transaction_type="Stock Out",
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        remarks=remarks,
        user_id=user_id
    )

    db.add(transaction)

    db.commit()

    await manager.broadcast({
        "type": "inventory_stock_updated",
        "item_id": item_id,
        "item_name": item.item_name,
        "transaction_type": "Stock Out",
        "quantity": quantity,
        "previous_stock": previous_stock,
        "new_stock": new_stock
    })

    return {
        "message": "Stock removed successfully.",
        "new_stock": new_stock
    }


# ============================================================
# TRANSACTION HISTORY
# ============================================================

@router.get("/{item_id}/transactions")
def get_transactions(
    item_id: int,
    db: Session = Depends(get_db)
):

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )

    transactions = (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.item_id == item_id
        )
        .order_by(
            desc(InventoryTransaction.created_at)
        )
        .all()
    )

    return [
        {
            "transaction_id": transaction.transaction_id,
            "item_id": transaction.item_id,
            "transaction_type": transaction.transaction_type,
            "quantity": transaction.quantity,
            "previous_stock": transaction.previous_stock,
            "new_stock": transaction.new_stock,
            "remarks": transaction.remarks,
            "user_id": transaction.user_id,
            "created_at": transaction.created_at
        }
        for transaction in transactions
    ]