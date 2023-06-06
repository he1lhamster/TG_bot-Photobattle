import asyncio
import aio_pika
import os
from typing import Optional
from aiohttp import TCPConnector
from aiohttp.client import ClientSession
import json
import random
from asyncio import Task


class Sender:
    def __init__(self):
        self.is_running = False
        self.outcoming_messages_task: Optional[Task] = None
        self.connection: Optional[aio_pika.connect] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.session: Optional[ClientSession] = None
        self.API_PATH = f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN','TOKEN')}/"

    async def start(self):
        while self.connection is None:
            try:
                self.connection = await aio_pika.connect(
                    "amqp://guest:guest@rabbitmq:5673/"
                )
                self.channel = await self.connection.channel()
                self.queue = await self.channel.declare_queue(
                    "outcoming_messages",
                )
                print("Connected to RabbitMQ")
            except aio_pika.exceptions.AMQPConnectionError:
                print("Connection failed, retry in 5 seconds")
                await asyncio.sleep(5)

        self.session = ClientSession(connector=TCPConnector(ssl=False))
        self.outcoming_messages_task = asyncio.create_task(self.run())

    async def stop(self):
        await self.outcoming_messages_task

        if self.session:
            await self.session.close()
        if self.connection:
            await self.connection.close()

    async def handle_send_message(self, message: aio_pika.IncomingMessage):
        async with message.process(ignore_processed=True):
            body = message.body.decode()
            body = json.loads(body)
            message_type = body.pop("message_type")

            correlation_id = message.correlation_id
            reply_to = message.reply_to

            if message_type == "message":
                response = await self.send_message(body)
            elif message_type == "messageMediaGroup":
                response = await self.send_media_group(body)
            elif message_type == "messagePhoto":
                response = await self.send_photo(body)
            elif message_type == "messageToDelete":
                response = await self.message_to_delete(body)
            elif message_type == "messageAnswerCallback":
                response = await self.send_answer_callback(body)
            elif message_type == "getUserAvatar":
                response = await self.get_user_avatar(body)
            else:
                response = None

            if response:
                response = json.dumps(response)
                await self.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=response.encode(), correlation_id=correlation_id
                    ),
                    routing_key=reply_to,
                )

            await message.ack()

    async def send_message(self, message):
        if not message["chat_id"]:
            message.pop("chat_id")
        if not message["reply_markup"]:
            message.pop("reply_markup")

        data = json.dumps(message)

        async with self.session.post(
            url=self.API_PATH + "sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
            return data

    async def send_answer_callback(self, message):
        if not message["text"]:
            message.pop("text")
        if not message["show_alert"]:
            message.pop("show_alert")

        data = json.dumps(message)

        async with self.session.post(
            url=self.API_PATH + "answerCallbackQuery",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
        return data

    async def send_media_group(self, message):
        data = json.dumps(message)
        async with self.session.post(
            url=self.API_PATH + "sendMediaGroup",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
        return data

    async def send_photo(self, message):
        data = json.dumps(message)
        async with self.session.post(
            url=self.API_PATH + "sendPhoto",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
        return data

    async def message_to_delete(self, message):
        data = json.dumps(message)
        async with self.session.post(
            url=self.API_PATH + "deleteMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
        return data

    async def get_user_avatar(self, message) -> str:  # return file_id
        data = json.dumps(message)
        async with self.session.post(
            url=self.API_PATH + "getUserProfilePhotos",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()

            if data["ok"]:
                if data["result"]["total_count"] > 0:
                    profile_photo = random.choice(data["result"]["photos"])
                    file_id = profile_photo[-1]["file_id"]
                    return file_id
                else:
                    return None
            else:
                return None

    async def run(self):
        while True:
            # await asyncio.sleep(1)
            await self.queue.consume(self.handle_send_message, timeout=10)

        await connection.close()


async def main():
    sender = Sender()
    task = asyncio.create_task(sender.start())

    try:
        await task
    except asyncio.CancelledError:
        print("Main task stopped")
    finally:
        await sender.stop()


if __name__ == "__main__":
    asyncio.run(main())
