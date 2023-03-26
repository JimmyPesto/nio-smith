# -*- coding: utf8 -*-
# bot specific imports
from core.plugin import Plugin
from nio import AsyncClient, RoomMessageText
from typing import Dict

# Python External Modules
import openai
# Python Internal Modules
import logging


logger = logging.getLogger(__name__)


plugin = Plugin(
    "aichat",
    "General",
    "Provide answers to all room-messages from aichat GPT bot",
)


def setup():
    # Change settings in aichat.yaml if required
    plugin.add_config("allowed_rooms", [], is_required=True)
    plugin.add_config("min_power_level", 50, is_required=True)
    plugin.add_config("openai_api_key", is_required=True)
    plugin.add_command(
        "aichat",
        switch,
        "`aichat` - activate/deactivate aichat GPT bot for this room",
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
    Enable or disable aichat GPT
    :param command:
    :return:
    """

    rooms_db: Dict[str, Dict[str, any]] = {}

    # get any existing room data
    if await plugin.read_data("rooms_db"):
        rooms_db = await plugin.read_data("rooms_db")
    # was `aichat` called with any other arguments?
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
        await plugin.respond_notice(command, "aichat GPT disabled")
    # else no existing hook (room was inactive before)
    # if no allowed_rooms list is given by configuration
    # OR this room is in allowed_rooms list
    elif not plugin.read_config("allowed_rooms") or command.room.room_id in plugin.read_config("allowed_rooms"):
        # activate aichat gpt for this room
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

        message = "Connection to aichat GPT enabled.  \n"
        message += f"**ATTENTION**: *ALL* future messages in this room will be sent to aichat GPT until disabled again."
        await plugin.respond_notice(command, message)


async def send_message_to_openai_gpt(client: AsyncClient, room_id: str, event: RoomMessageText):
    """
    Send a received message to aichat gpt if translation is active on room
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
        # check if bot username was mentioned
        # client.user_id = @<username>:<matrix-home-server-domain>
        response = await client.get_displayname()
        simple_client_id = response.displayname
        logger.debug(f"incoming message before cleanup: {message}")
        if event.source['content'].get('m.relates_to', False):
            # if message relates to prev message (answer)
            # -> remove prev messages
            message = remove_lines_with_answer_character(message)
        if simple_client_id in message:
            # bot was mentioned
            openai.api_key = plugin.read_config("openai_api_key")
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a funny assistant called {simple_client_id}."},
                    {"role": "user", "content": message},
                ]
            )
            tokens_spend = response['usage']['total_tokens']
            answer = response['choices'][0]['message']['content']
            await plugin.send_notice(client, room_id, answer+f" [{tokens_spend}]")
            return


# example response:
#   "choices": [
#     {
#       "finish_reason": "stop",
#       "index": 0,
#       "message": {
#         "content": "The Los Angeles Dodgers won the World Series in 2020.",
#         "role": "assistant"
#       }
#     }
#   ],
#   "created": 1679677002,
#   "id": "chatcmpl-6xf0U5TQA95zEVrarI1EEKcHrNHHT",
#   "model": "gpt-3.5-turbo-0301",
#   "object": "chat.completion",
#   "usage": {
#     "completion_tokens": 13,
#     "prompt_tokens": 29,
#     "total_tokens": 42
#   }
# }

def remove_lines_with_answer_character(string):
    lines = string.split("\n")
    new_lines = []
    for line in lines:
        if line and line[0] != ">":
            new_lines.append(line)
    return "\n".join(new_lines)

setup()
