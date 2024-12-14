from fastapi import WebSocket
from typing import Set
import asyncio
import logging

class WebSocketManager:
    _instance = None
    _websockets: Set[WebSocket] = set()
    _active_items = {}
    _lock = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._lock = asyncio.Lock()
            print("Created new WebSocketManager instance")
        return cls._instance

    async def add_websocket(self, websocket: WebSocket):
        async with self._lock:
            self._websockets.add(websocket)
            
            # Send current status to new connection
            if self._active_items:
                await websocket.send_json({
                    'type': 'processing_status',
                    'items': list(self._active_items.values())
                })

    async def remove_websocket(self, websocket: WebSocket):
        async with self._lock:
            self._websockets.discard(websocket)

    async def broadcast_status(self, message):
        if not self._websockets:
            return
            
        # Update active items if this is a processing_status message
        if message.get('type') == 'processing_status' and 'items' in message:
            # Update items without clearing all existing ones
            for item in message['items']:
                if 'id' in item:
                    # Remove completed items
                    if item.get('status', {}).get('status') == 'Completed':
                        if item['id'] in self._active_items:
                            del self._active_items[item['id']]
                    else:
                        self._active_items[item['id']] = item
            
            # Update the message to include all current items
            message['items'] = list(self._active_items.values())
        
        disconnected = set()
        
        # Iterate over a copy of the set to avoid modification during iteration
        for websocket in list(self._websockets):
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f'Error broadcasting to websocket: {e}')
                disconnected.add(websocket)
        
        # Handle disconnected websockets outside the main loop
        for websocket in disconnected:
            self._websockets.discard(websocket)

    def get_active_items(self):
        return self._active_items.copy()

    def remove_active_item(self, item_id: str):
        """Remove an item from active items when processing completes"""
        if item_id in self._active_items:
            del self._active_items[item_id]
            print(f"Successfully removed item {item_id} from active items")
        else:
            print(f"Item {item_id} not found in active items")

    async def update_item_status(self, item_id: str, status_update: dict):
        """Update status for a specific item"""
        print(f"Updating status for item {item_id}: {status_update}")
        async with self._lock:
            if item_id in self._active_items:
                self._active_items[item_id].update(status_update)
                await self.broadcast_status({
                    'type': 'processing_status',
                    'items': list(self._active_items.values())
                })
                print(f"Status updated for item {item_id}")
            else:
                print(f"Item {item_id} not found for status update")