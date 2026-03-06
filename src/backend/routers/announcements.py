"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable dict"""
    if announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements that are within their date range"""
    current_time = datetime.utcnow().isoformat() + "Z"
    
    # Find announcements that are active and within date range
    announcements = announcements_collection.find({
        "active": True,
        "expiration_date": {"$gte": current_time}
    })
    
    result = []
    for announcement in announcements:
        # Check if start_date exists and if we're past it
        if "start_date" in announcement and announcement["start_date"]:
            if announcement["start_date"] > current_time:
                continue
        result.append(serialize_announcement(announcement))
    
    return result


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Get all announcements sorted by creation date (newest first)
    announcements = announcements_collection.find().sort("_id", -1)
    
    return [serialize_announcement(announcement) for announcement in announcements]


@router.post("")
def create_announcement(
    username: str,
    message: str,
    expiration_date: str,
    start_date: str = None,
    active: bool = True
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate expiration_date format
    try:
        datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration_date format")
    
    # Validate start_date format if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    # Create announcement document
    announcement = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "active": active,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    del announcement["_id"]
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    username: str,
    message: str = None,
    expiration_date: str = None,
    start_date: str = None,
    active: bool = None
) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Build update document
    update_doc = {}
    if message is not None:
        update_doc["message"] = message
    if expiration_date is not None:
        try:
            datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
            update_doc["expiration_date"] = expiration_date
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration_date format")
    if start_date is not None:
        if start_date:
            try:
                datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        update_doc["start_date"] = start_date
    if active is not None:
        update_doc["active"] = active
    
    if not update_doc:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_doc["updated_by"] = username
    update_doc["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    # Update the announcement
    result = announcements_collection.find_one_and_update(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_doc},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return serialize_announcement(result)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Delete the announcement
    result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
