from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from api.serializers import MessageSerializer


def send_message(instance=None):
    channel_layer = get_channel_layer()

    serializer = MessageSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "messages",
        {
            "type": "message.created",
            "data": {
                "entity": serialized_data,
                "message": "New message",
            }
        }
    )


def delete_message(instance=None):
    channel_layer = get_channel_layer()

    serializer = MessageSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "messages",
        {
            "type": "message.deleted",
            "data": {
                "entity": serialized_data,
                "message": "Deleted message",
            }
        }
    )