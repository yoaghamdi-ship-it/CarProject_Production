import json
from channels.generic.websocket import AsyncWebsocketConsumer

class InventoryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("inventory_updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("inventory_updates", self.channel_name)

    async def send_inventory_update(self, event):
        # إرسال البيانات الجديدة للمتصفح
        await self.send(text_data=json.dumps(event["data"]))