# -*- coding: utf8 -*-
# bot specific imports
from core.plugin import Plugin
from nio import AsyncClient, RoomMessageText
from nio.responses import RoomContextResponse
from typing import Dict

# Python External Modules
import openai
# Python Internal Modules
import re
import logging


logger = logging.getLogger(__name__)

ROOM_DB_TYPE = Dict[str, any]
ROOMS_DB_TYPE = Dict[str, ROOM_DB_TYPE]

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
    plugin.add_config("max_tokens", 1000, is_required=True)
    plugin.add_config("default_model", "gpt-3.5-turbo", is_required=True)
    plugin.add_config("default_system_role_content", "You are a funny assistant called {bot_user_id}.",
                      is_required=True)
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

    rooms_db: ROOMS_DB_TYPE = {}

    # get any existing room data
    if await plugin.read_data("rooms_db"):
        rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")

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
        # was `aichat` called with any other arguments?
        if len(command.args) == 0:  # no additional argument
            # load default value model_name from config
            model_name: str = plugin.read_config("default_model")
        elif len(command.args) == 1:  # additional argument included
            model_name = command.args[0]
        else:
            await plugin.respond_notice(command, f"Invalid arguments specified.")
            return
        openai.api_key = plugin.read_config("openai_api_key")
        models = openai.Model.list()
        if model_name not in [model.id for model in models["data"]]:
            await plugin.respond_notice(command, f"{model_name} openai model doesn't exist!")
            return

        default_system_role_content: str = plugin.read_config("default_system_role_content")
        # activate aichat gpt for this room
        # persist new state
        rooms_db[command.room.room_id] = {
            "room_id": command.room.room_id,
            "is_active": True,
            "model_name": model_name,
            "system_role_content": default_system_role_content
        }
        await plugin.store_data("rooms_db", rooms_db)
        # activate the hook
        plugin.add_hook(
            "m.room.message",
            send_message_to_openai_gpt,
            room_id_list=[command.room.room_id],
            hook_type="dynamic",
        )

        response = await command.client.get_displayname()
        client_id = response.displayname
        message = "Connection to aichat GPT enabled.  \n"
        message += f"**ATTENTION**: *ALL* future messages including my name {client_id} in this room"\
                   f" will be sent to openai {model_name} until disabled again, don't share any secrets."
        await plugin.respond_notice(command, message)


async def send_message_to_openai_gpt(client: AsyncClient, room_id: str, event: RoomMessageText):
    """
    Send a received message to aichat gpt if translation is active on room
    :param client:
    :param room_id:
    :param event:
    :return:
    """
    logger.info(event)
    # if allowed rooms is empty or room is in allowed rooms
    if plugin.read_config("allowed_rooms") == [] or room_id in plugin.read_config("allowed_rooms"):
        rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
        if not rooms_db or rooms_db.get(room_id, None) is None:  # no data found for this room
            await plugin.respond_notice(client, f"No data found for this room, disabling hook...")
            plugin.del_hook("m.room.message", send_message_to_openai_gpt, room_id_list=[room_id])
            return
        room_db: ROOM_DB_TYPE = rooms_db[room_id]
        model_name: str = room_db.get('model_name') or plugin.read_config("default_model")
        system_role_content: str = room_db.get('system_role_content') or \
            plugin.read_config("default_system_role_content")
        max_tokens: int = plugin.read_config("max_tokens")
        logger.info(f"incoming message before cleanup: {event.body}")
        message = remove_lines_with_answer_character(event.body)
        # check if bot username was mentioned
        # client.user_id = @<username>:<matrix-home-server-domain>
        response = await client.get_displayname()
        simple_client_id = response.displayname
        # message does not include relates_to quote parts "> text"
        # -> client ID must always be included in latest message itself!
        if simple_client_id in message:
            # bot was mentioned
            openai.api_key = plugin.read_config("openai_api_key")
            aichat = AiMessages(system_role_content=system_role_content,
                                assistant_client_id=simple_client_id)
            aichat.append_user_message(message)
            if event.source['content'].get('m.relates_to', False):
                # current message relates to a previous message
                relates_to: RoomContextResponse = await client.room_context(
                    room_id=room_id, event_id=event.source['content']['m.relates_to']['m.in_reply_to']['event_id'],
                    limit=1)
                relates_to_sender_id = relates_to.event.sender
                relates_to_message = relates_to.event.body
                aichat.insert_related_message_as_context(source_client_id=relates_to_sender_id,
                                                         content=relates_to_message)
            response = await openai.ChatCompletion.acreate(
                model=model_name,
                max_tokens=max_tokens,
                messages=aichat.messages
            )
            logger.warning(response)
            answer = response['choices'][0]['message']['content']
            logger.warning(answer)
            logger.warning(indent_between_code_blocks(answer))
            finish_reason: str = response['choices'][0]['finish_reason']
            tokens_spend = response['usage']['total_tokens']
            expanded_message = f"Response info: {model_name}, {finish_reason},  tokens spend [{tokens_spend}]"
            await plugin.send_message(client, room_id, indent_between_code_blocks(answer), expanded_message,
                                      markdown_convert=True)
        return


def remove_lines_with_answer_character(string):
    lines = string.split("\n")
    new_lines = []
    for line in lines:
        if line and line[0] != ">":
            new_lines.append(line)
    return "\n".join(new_lines)


def new_ai_message(role: str, content: str) -> dict:
    return {"role": role, "content": remove_lines_with_answer_character(content)}


class AiMessages:
    def __init__(self, system_role_content: str, assistant_client_id: str):
        self.assistant_client_id: str = assistant_client_id
        self.messages = []
        # first message should be system role
        self.append_message(role="system", content=system_role_content)

    def append_message(self, role: str, content: str):
        self.messages.append(new_ai_message(role=role, content=content.format(bot_user_id=self.assistant_client_id)))

    def insert_related_message_as_context(self, source_client_id: str, content: str):
        if self.assistant_client_id in source_client_id:  # message from bot/assistant
            role = "assistant"
        else:  # message from any user
            role = "user"
        self.messages.insert(1, new_ai_message(role=role, content=content))

    def append_user_message(self, content: str):
        self.append_message(role="user", content=content)


# https://daringfireball.net/projects/markdown/syntax#precode
# be careful, codeblocks work different arround here
# all lines between "```" must be indented by one tab
def indent_between_code_blocks(text):
    regular_codeblock_sign = "```"
    block_indices = [0] + [x.start() for x in re.finditer(regular_codeblock_sign, text)]
    blocks = [text[block_indices[i]:block_indices[i+1]] for i in range(len(block_indices)-1)]
    if len(blocks) == 0:
        # no code blocks found
        return text
    else:
        indented_blocks = []
        for i, block in enumerate(blocks):
            if i % 2 == 0:
                indented_blocks.append(block)
            else:
                indented_blocks.append('\t' + block.replace('\n', '\n\t'))
        return ''.join(indented_blocks).replace(regular_codeblock_sign, "")


setup()
