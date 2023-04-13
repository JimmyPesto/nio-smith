# -*- coding: utf8 -*-
# bot specific imports
from core.plugin import Plugin
from nio import AsyncClient, RoomMessageText
from nio.responses import RoomGetEventResponse, RoomContextResponse
from typing import Dict

# Python External Modules
import openai
# Python Internal Modules
import re
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
    logger.error(event)
    rooms_db: Dict[str, Dict[str, any]] = {}

    if await plugin.read_data("rooms_db"):
        rooms_db = await plugin.read_data("rooms_db")

    # if allowed rooms is empty or room is in allowed rooms
    if plugin.read_config("allowed_rooms") == [] or room_id in plugin.read_config("allowed_rooms"):
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
            aichat = AiMessages(system_role_content=f"You are a funny assistant called {simple_client_id}.",
                                assistant_client_id=simple_client_id)
            aichat.append_user_message(message)
            logger.error(f"relates_to: {event.source['content'].get('m.relates_to')}")
            logger.error(f"message: {event.source['content'].get('m.room.message')}")
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
                model="gpt-3.5-turbo",  # ToDo add config
                max_tokens=600,  # ToDo add to config
                messages=aichat.messages
            )
            logger.warning(aichat.messages)
            tokens_spend = response['usage']['total_tokens']
            answer = response['choices'][0]['message']['content']
            await plugin.send_message(client, room_id, indent_between_code_blocks(answer), markdown_convert=True)
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
        self.messages.append(new_ai_message(role=role, content=content))

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
    block_indices = [0] +[x.start() for x in re.finditer(regular_codeblock_sign, text)]
    blocks = [text[block_indices[i]:block_indices[i+1]] for i in range(len(block_indices)-1)]
    indented_blocks = []
    for i, block in enumerate(blocks):
        if i % 2 == 0:
            indented_blocks.append(block)
        else:
            indented_blocks.append('\t' + block.replace('\n', '\n\t'))
    return ''.join(indented_blocks).replace(regular_codeblock_sign, "")


setup()
