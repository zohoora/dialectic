"""
Base Library - Common storage pattern for libraries.

Provides a generic base class for JSON-backed storage libraries
with add/get/remove/search patterns.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel


logger = logging.getLogger(__name__)


# Type variable for library item type
T = TypeVar("T", bound=BaseModel)


class BaseLibrary(ABC, Generic[T]):
    """
    Abstract base class for JSON-backed storage libraries.
    
    Provides common functionality for:
    - Storage and persistence
    - Add/get/remove operations
    - Basic search patterns
    
    Subclasses must implement:
    - get_item_id(): How to extract ID from an item
    - _deserialize_item(): How to deserialize from JSON
    - _serialize_item(): How to serialize to JSON (optional override)
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        storage_key: str = "items",
    ):
        """
        Initialize the library.
        
        Args:
            storage_path: Path to JSON file for persistence
            storage_key: Key name in JSON for items dict
        """
        self.storage_path = storage_path
        self.storage_key = storage_key
        self._items: dict[str, T] = {}
        
        if storage_path and storage_path.exists():
            self._load_from_storage()
    
    @abstractmethod
    def get_item_id(self, item: T) -> str:
        """Extract the unique ID from an item."""
        pass
    
    @abstractmethod
    def _deserialize_item(self, data: dict) -> T:
        """Deserialize an item from JSON data."""
        pass
    
    def _serialize_item(self, item: T) -> dict:
        """Serialize an item to JSON data. Override if needed."""
        return item.model_dump()
    
    def add(self, item: T) -> str:
        """
        Add an item to the library.
        
        Args:
            item: The item to add
            
        Returns:
            The item ID
        """
        item_id = self.get_item_id(item)
        self._items[item_id] = item
        self._save_to_storage()
        
        logger.info(f"Added {self.__class__.__name__} item: {item_id}")
        return item_id
    
    def get(self, item_id: str) -> Optional[T]:
        """
        Get an item by ID.
        
        Args:
            item_id: ID of the item
            
        Returns:
            The item if found, None otherwise
        """
        return self._items.get(item_id)
    
    def remove(self, item_id: str) -> bool:
        """
        Remove an item from the library.
        
        Args:
            item_id: ID of the item to remove
            
        Returns:
            True if removed, False if not found
        """
        if item_id in self._items:
            del self._items[item_id]
            self._save_to_storage()
            logger.info(f"Removed {self.__class__.__name__} item: {item_id}")
            return True
        return False
    
    def get_all(self) -> list[T]:
        """Get all items in the library."""
        return list(self._items.values())
    
    def count(self) -> int:
        """Get the number of items in the library."""
        return len(self._items)
    
    def clear(self) -> None:
        """Clear all items from the library."""
        self._items.clear()
        self._save_to_storage()
        logger.info(f"Cleared all items from {self.__class__.__name__}")
    
    def _load_from_storage(self) -> None:
        """Load items from JSON file."""
        if not self.storage_path:
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            items_data = data.get(self.storage_key, {})
            
            for item_id, item_data in items_data.items():
                try:
                    self._items[item_id] = self._deserialize_item(item_data)
                except Exception as e:
                    logger.warning(f"Failed to deserialize item {item_id}: {e}")
            
            logger.info(
                f"Loaded {len(self._items)} items into {self.__class__.__name__}"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse storage file: {e}")
        except Exception as e:
            logger.error(f"Failed to load from storage: {e}")
    
    def _save_to_storage(self) -> None:
        """Save items to JSON file."""
        if not self.storage_path:
            return
        
        try:
            # Ensure parent directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing data to preserve other keys
            existing_data = {}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, "r") as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, Exception):
                    pass
            
            # Update with current items
            existing_data[self.storage_key] = {
                item_id: self._serialize_item(item)
                for item_id, item in self._items.items()
            }
            
            # Write back
            with open(self.storage_path, "w") as f:
                json.dump(existing_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save to storage: {e}")


def keyword_match_score(text: str, keywords: list[str]) -> float:
    """
    Calculate a simple keyword match score.
    
    Args:
        text: Text to search in
        keywords: Keywords to look for
        
    Returns:
        Score between 0 and 1
    """
    if not keywords or not text:
        return 0.0
    
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / len(keywords)

