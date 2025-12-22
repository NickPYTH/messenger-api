from channels.generic.websocket import AsyncJsonWebsocketConsumer


class MessagesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("messages", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("messages", self.channel_name)

    async def message_created(self, event):

        await self.send_json({
            "type": "message_created",
            "entity": event["data"]["entity"],
            "message": event["data"]["message"]
        })