import asyncio
from asyncio import Task
from typing import Optional
from aiohttp.client import ClientSession
from aiohttp import TCPConnector

# from dataclassess import Update, UpdateObject, Player
import aio_pika
import os
import json

# from dataclasses import asdict

TIMEOUT = 60


class Poller:
    def __init__(self):
        self.poll_task: Optional[Task] = None
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.session: Optional[ClientSession] = None
        self.offset: Optional[int] = None
        self.API_PATH = f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN','TOKEN')}/"
        # self.API_PATH = f"https://api.telegram.org/bot{TOKEN}/"

    async def start(self):
        while self.connection is None:
            try:
                self.connection = await aio_pika.connect(
                    "amqp://guest:guest@rabbitmq:5673/",
                )
                self.channel = await self.connection.channel()
                self.queue = await self.channel.declare_queue(
                    "incoming_updates",
                )
                print("Connected to RabbitMQ")
            except aio_pika.exceptions.AMQPConnectionError:
                # retry after 3 sec
                await asyncio.sleep(3)

        self.session = ClientSession(connector=TCPConnector(ssl=False))
        self.poll_task = asyncio.create_task(self.poll())

    async def stop(self):
        await self.poll_task

        if self.session:
            await self.session.close()
        if self.connection:
            await self.connection.close()

    async def poll(self):
        print("start polling")
        while True:
            try:
                updates = await self.get_updates()
                for update in updates:
                    # update = self.to_update_dataclass(update)
                    # body = json.dumps(asdict(update))
                    body = json.dumps(update)
                    await self.channel.default_exchange.publish(
                        aio_pika.Message(body=body.encode()),
                        routing_key=self.queue.name,
                    )
            except asyncio.CancelledError:
                break

    async def get_updates(self) -> list[dict]:
        async with self.session.post(
            url=self.API_PATH + "getUpdates",
            data={"offset": self.offset, "timeout": TIMEOUT},
        ) as response:
            raw_updates = await response.json()
            updates = []
            try:
                for update in raw_updates["result"]:
                    self.offset = update["update_id"] + 1
                    updates.append(update)
                return updates

            except KeyError as e:
                pass


async def main():
    poller = Poller()
    task = asyncio.create_task(poller.start())

    try:
        await task
    except asyncio.CancelledError:
        print("Main task stopped")
    finally:
        await poller.stop()


if __name__ == "__main__":
    asyncio.run(main())
