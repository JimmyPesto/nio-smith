# -*- coding: utf8 -*-
from core.plugin import Plugin
from nio import AsyncClient, RoomMessageText
from typing import Dict
import logging

logger = logging.getLogger(__name__)
plugin = Plugin(
    "openai",
    "General",
    "Provide answers to all room-messages from openai GPT bot",
)


def setup():
    # Change settings in openai.yaml if required
    plugin.add_config("allowed_rooms", [], is_required=True)
    plugin.add_config("min_power_level", 50, is_required=True)
    # plugin.add_config()
    plugin.add_command(
        "openai",
        switch,
        "`openai` - activate/deactivate openai GPT bot for this room",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )


"""
roomsdb = {
    room_id: {
        "room_id": command.room.room_id,
        "is_active": True
    }
}
"""


async def switch(command):
    """
    Enable or disable openai GPT
    :param command:
    :return:
    """

    rooms_db: Dict[str, Dict[str, any]] = {}

    # get any existing room data
    if await plugin.read_data("rooms_db"):
        rooms_db = await plugin.read_data("rooms_db")
    # was `openai` called with any other arguments?
    # if len(command.args) == 0:  # no additional argument
        # load default values from config
        # source_langs: List[str] = plugin.read_config("default_source")
        # dest_lang: str = plugin.read_config("default_dest")
        # bidirectional: bool = plugin.read_config("default_bidirectional")

    if len(command.args) > 0:  # additional arguments included
        # try:
        #     if command.args[0] == "bi":
        #         pass
        # except IndexError:
        #     await plugin.respond_notice(command, "Syntax: `!translate [[bi] source_lang... dest_lang]`")
        #     return False
        await plugin.respond_notice(command, f"Invalid arguments specified.")
        return

    # if existing hook (room was activated before)
    if plugin.has_hook("m.room.message", send_message_to_openai_gpt, [command.room.room_id]):
        plugin.del_hook("m.room.message", send_message_to_openai_gpt, room_id_list=[command.room.room_id])
        del rooms_db[command.room.room_id]
        await plugin.store_data("rooms_db", rooms_db)
        await plugin.respond_notice(command, "openai GPT disabled")
    # else no existing hook (room was inactive before)
    # if no allowed_rooms list is given by configuration
    # OR this room is in allowed_rooms list
    elif not plugin.read_config("allowed_rooms") or command.room.room_id in plugin.read_config("allowed_rooms"):
        # activate openai gpt for this room
        # persist new state
        rooms_db[command.room.room_id] = {
            "room_id": command.room.room_id,
            "is_active": True
        }
        await plugin.store_data("rooms_db", rooms_db)
        # activate the hook
        plugin.add_hook(
            "m.room.message",
            send_message_to_openai_gpt,
            room_id_list=[command.room.room_id],
            hook_type="dynamic",
        )

        message = "Connection to openai GPT enabled.  \n"
        message += f"**ATTENTION**: *ALL* future messages in this room will be sent to openai GPT until disabled again."
        await plugin.respond_notice(command, message)


async def send_message_to_openai_gpt(client: AsyncClient, room_id: str, event: RoomMessageText):
    """
    Send a received message to openai gpt if translation is active on room
    :param client:
    :param room_id:
    :param event:
    :return:
    """

    rooms_db: Dict[str, Dict[str, any]] = {}

    if await plugin.read_data("rooms_db"):
        rooms_db = await plugin.read_data("rooms_db")

    # if allowed rooms is empty or room is in allowed rooms
    if plugin.read_config("allowed_rooms") == [] or room_id in plugin.read_config("allowed_rooms"):
        message = event.body
        # check if bot username was mentioned as first word in incoming message?
        split_message = message.split(" ")
        # client.user_id = @<username>:<matrix-home-server-domain>
        simple_client_id = client.user_id.replace("@", "").split(":")[0]
        if simple_client_id in split_message[0]:
            # bot was meantioned
            await plugin.send_notice(client, room_id, "seems like you love me because you know my name")


setup()
