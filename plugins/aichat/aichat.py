# -*- coding: utf8 -*-
# bot specific imports
from core.plugin import Plugin
from core.bot_commands import Command
from nio import AsyncClient, RoomMessageText, RoomMemberEvent
from nio.responses import RoomContextResponse, RoomContextError
from typing import Dict


# Python External Modules
import openai
# Python Internal Modules
from functools import wraps
import logging

logger = logging.getLogger(__name__)

ROOM_DB_TYPE = Dict  # [str, any]
ROOMS_DB_TYPE = Dict[str, ROOM_DB_TYPE] | None  # None if no data saved before

MESSAGE_HISTORY_LEN_MAX = 20
ANSWER_CHARACTER = ">"
REACTION_SUCCESS = "✅"
ERROR_MESSAGE_READ_CONFIG_INACTIVE_ROOM = \
    "I can only read this rooms configuration when `aichat` was activated before!"
ERROR_MESSAGE_SET_CONFIG_INACTIVE_ROOM = \
    "I can only update this rooms configuration when `aichat` was activated before!"
DEFAULT_CHAT_MODEL = "gpt-3.5-turbo"

plugin = Plugin(
    "aichat",
    "General",
    "Provide answers to all room-messages from aichat GPT bot",
)


def setup():
    # Change settings in aichat.yaml if required
    plugin.add_config("openai_api_key", is_required=True)
    plugin.add_config("allowed_rooms", [], is_required=False)
    plugin.add_config("min_power_level", 50, is_required=False)
    plugin.add_config("max_tokens", 1000, is_required=False)
    plugin.add_config("default_message_history_len", 0, is_required=False)
    plugin.add_config("default_model", DEFAULT_CHAT_MODEL, is_required=False)
    plugin.add_config("default_system_role_content", "You are a funny assistant called {bot_user_id}.",
                      is_required=False)
    plugin.add_command(
        "aichat",
        switch,
        f"activate/deactivate aichat bot for this room [optional model name]",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )
    plugin.add_command(
        "aichat-set-system-role",
        set_system_role_content,
        """Change the default system role message content. \
        The placeholder {bot_user_id} will automatically be replaced by bots username""",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )
    plugin.add_command(
        "aichat-print-system-role",
        print_system_role_content,
        "Return the currently configured content of the bots system role",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )
    plugin.add_command(
        "aichat-print-message-history",
        get_message_history_len,
        "Return the currently configured number of previous messages included in any openai request",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )
    plugin.add_command(
        "aichat-set-message-history",
        set_message_history_len,
        """Set the number of how many messages from the chatroom history shall be included in your openai request \
        [max. = 20]""",
        room_id=plugin.read_config("allowed_rooms"),
        power_level=plugin.read_config("min_power_level"),
    )


"""
roomsdb = {  # ROOMS_DB_TYPE
    room_id: {  # ROOM_DB_TYPE
        "is_active": True,
        "model_name": "gpt-3.5-turbo"
        "system_role_content": "You are a funny assistant called {bot_user_id}."
        "model_history_len": 0
    }
}
"""


# plugin helpers?
async def get_bot_client_id_from_command(command: Command) -> str:
    return await get_bot_client_id(command.client)


# plugin helpers?
async def get_bot_client_id(client: AsyncClient) -> str:
    # client.user_id = @<username>:<matrix-home-server-domain>
    # displayname = <username>
    response = await client.get_displayname()
    return str(response.displayname)


# plugin helpers?
# read_room_db_from_command
async def get_room_db_from_command(command: Command) -> ROOM_DB_TYPE:
    return await get_room_db_from_room_id(command.room.room_id)


# plugin helpers?
# read_room_db_from_room_id
async def get_room_db_from_room_id(room_id: str) -> ROOM_DB_TYPE:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    try:
        return rooms_db[room_id]
    except KeyError:
        logger.debug(f"No room db found for {room_id}")
        return {}


# plugin helpers?
# store_room_db_from_command
async def save_room_db_from_command(command: Command, room_db: ROOM_DB_TYPE) -> bool:
    return await store_room_db_from_room_id(command.room.room_id, room_db)


# plugin helpers?
# store_room_db_from_room_id
async def store_room_db_from_room_id(room_id: str, room_db: ROOM_DB_TYPE) -> bool:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    try:
        rooms_db[room_id] = room_db
    except TypeError:
        rooms_db = {room_id: room_db}
    return await plugin.store_data("rooms_db", rooms_db)


# plugin helpers?
# store_room_db_from_db
async def update_room_db(command: Command, update_db: ROOM_DB_TYPE) -> bool:
    room_db: ROOM_DB_TYPE = await get_room_db_from_command(command)
    room_db.update(update_db)
    return await save_room_db_from_command(command, room_db)


# plugin helpers?
async def clear_room_db_from_command(command: Command) -> bool:
    return await clear_room_db_from_room_id(command.room.room_id)


async def clear_room_db_from_room_id(room_id: str) -> bool:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    del rooms_db[room_id]
    return await plugin.store_data("rooms_db", rooms_db)


# aichat command dependency
def is_aichat_active_in_current_room(command: Command) -> bool:
    # if existing hook (room was activated before)
    return plugin.has_hook("m.room.message", send_message_to_openai_gpt, [command.room.room_id])


TYPING_TIMEOUT_DEFAULT = 30000  # [ms]


# plugin helpers
async def set_typing(command: Command, typing_state: bool = True, timeout: int | None = TYPING_TIMEOUT_DEFAULT):
    await command.client.room_typing(command.room.room_id, timeout=timeout, typing_state=typing_state)


def add_typing_command_response(func):
    @wraps(func)
    async def wrapper(*args):
        command: Command = args[0]
        await set_typing(command, timeout=TYPING_TIMEOUT_DEFAULT)
        result = await func(command)
        await set_typing(command, typing_state=False)
        return result

    return wrapper


# ToDo ideally pass all (unknown) arguments from wrapper to func
def add_typing_client_response(func):
    @wraps(func)
    async def wrapper(client, room_id, event):
        await client.room_typing(room_id, timeout=TYPING_TIMEOUT_DEFAULT)
        result = await func(client, room_id, event)
        await client.room_typing(room_id, typing_state=False)
        return result
    return wrapper


# aichat command dependency
async def format_with_display_name(client: AsyncClient, text: str) -> str:
    # replaces occurrences of {bot_client_id} by display name
    simple_client_id = await get_bot_client_id(client)
    return f"'{text.format(bot_user_id=simple_client_id)}'"


# aichat command
@add_typing_command_response
async def print_system_role_content(command: Command):
    # if existing hook (room was activated before)
    if is_aichat_active_in_current_room(command):
        room_db: ROOM_DB_TYPE = await get_room_db_from_command(command)  # might be empty dict
        current_system_role_content: str | None = room_db.get("system_role_content", None)
        if current_system_role_content is None:  # no data found for this room
            current_system_role_content = plugin.read_config("default_system_role_content")
        try:
            formatted_with_name = await format_with_display_name(command.client, current_system_role_content)
            await plugin.respond_message(command, "My system role message is: " + formatted_with_name)
        except KeyError:
            await plugin.respond_message(command, "Update of system role message failed: use the name placeholder"
                                                  " \"{bot_client_id}\" including the \" signs.")
    else:
        await plugin.respond_message(
            command, ERROR_MESSAGE_READ_CONFIG_INACTIVE_ROOM)


# aichat command
async def set_system_role_content(command: Command):
    # if existing hook (room was activated before)
    if is_aichat_active_in_current_room(command):
        if len(command.args) > 0:
            new_system_role_content = " ".join(arg for arg in command.args)
        else:
            await print_system_role_content(command)
            new_system_role_content = plugin.read_config("default_system_role_content")
        try:
            formatted_with_name = await format_with_display_name(command.client, new_system_role_content)
        except KeyError:
            await plugin.respond_message(command, "Update of system role message failed: use the name placeholder"
                                                  " \"{bot_client_id}\" including the \" signs.")
            return
        await update_room_db(command, {
            "system_role_content": formatted_with_name
        })
        await plugin.respond_reaction(command,  REACTION_SUCCESS)
    else:
        # aichat is inactive for this room
        await plugin.respond_message(
            command, ERROR_MESSAGE_SET_CONFIG_INACTIVE_ROOM)


# aichat command
async def set_message_history_len(command: Command):
    if is_aichat_active_in_current_room(command):
        if len(command.args) == 1:
            try:
                new_message_history_len = int(command.args[0])
                if new_message_history_len > MESSAGE_HISTORY_LEN_MAX:
                    new_message_history_len = MESSAGE_HISTORY_LEN_MAX
                new_room_data = {"message_history_len": new_message_history_len}
                await update_room_db(command, new_room_data)
                await plugin.respond_reaction(command, REACTION_SUCCESS)
                return
            except ValueError:
                logger.error(f"Failed parsing '{command.args[0]}' as int")
        await plugin.respond_message(
            command, "Updating message history failed, please provide a single integer as argument!")
        return
    else:
        # aichat is inactive for this room
        await plugin.respond_message(
            command, ERROR_MESSAGE_SET_CONFIG_INACTIVE_ROOM)


# aichat command
@add_typing_command_response
async def get_message_history_len(command: Command):
    if is_aichat_active_in_current_room(command):
        room_db = await get_room_db_from_command(command)  # can be empty dict
        current_message_history_len: int | None = room_db.get("message_history_len", None)
        if current_message_history_len is None:
            current_message_history_len = plugin.read_config("default_message_history_len")
        await plugin.respond_message(
            command, f"Currently {current_message_history_len} previous messages are included in any openai request.")
        return
    else:
        # aichat is inactive for this room
        await plugin.respond_message(
            command, ERROR_MESSAGE_READ_CONFIG_INACTIVE_ROOM)


async def activate_aichat_in_current_room(command: Command, model_name: str):
    openai.api_key = plugin.read_config("openai_api_key")
    models = openai.Model.list()
    if model_name not in [model.id for model in models["data"]]:
        await plugin.respond_notice(command, f"{model_name} openai model doesn't exist!")
        return
    # activate aichat for this room and persist "empty" state
    empty_room_db = {
        "is_active": True,
        "model_name": model_name
    }
    await save_room_db_from_command(command, empty_room_db)
    # activate the hook
    plugin.add_hook(
        "m.room.message",
        send_message_to_openai_gpt,
        room_id_list=[command.room.room_id],
        hook_type="dynamic",
    )

    # Dynamically add a reaction hook for one specific event-id
    plugin.add_hook(
        "m.room.member",
        hook_member,
        room_id_list=[command.room.room_id],
        hook_type="dynamic"
    )

    message = "aichat enabled  \n"
    message += await get_how_to_interact_with_aichat_message(command.client, command.room.room_id)
    await plugin.respond_notice(command, message)


def get_nr_of_users_in_room(command: Command) -> int:
    return len(command.room.users)


def get_nr_of_users_in_room_from_client(client: AsyncClient, room_id: str) -> int:
    return len(client.rooms[room_id].users)


MESSAGE_TEMPLATE_PRIVATE_CHAT: str = """
**ATTENTION**: ALL messages within this private chat 
will be sent to openai {default_model}.\n
Don't share any secrets.
"""

MESSAGE_TEMPLATE_GROUP_CHAT: str = """
**ATTENTION**: ALL messages including my name '{client_id}' in this group chat 
will be sent to openai {default_model}.\n
Don't share any secrets.
"""


async def get_how_to_interact_with_aichat_message(client: AsyncClient, room_id: str) -> str:
    client_id = await get_bot_client_id(client)
    default_model = plugin.read_config('default_model')
    nr_of_users_in_room = get_nr_of_users_in_room_from_client(client, room_id)
    if nr_of_users_in_room == 2:
        # private chat, no extra trigger needed
        message = MESSAGE_TEMPLATE_PRIVATE_CHAT.format(default_model=default_model)
    else:
        message = MESSAGE_TEMPLATE_GROUP_CHAT.format(client_id=client_id, default_model=default_model)
    return message


async def deactivate_aichat_in_current_room(command: Command) -> bool:
    removed = plugin.del_hook("m.room.message", send_message_to_openai_gpt, room_id_list=[command.room.room_id])
    removed_member_hook = plugin.del_hook("m.room.member", hook_member, room_id_list=[command.room.room_id])
    await clear_room_db_from_command(command)
    await plugin.respond_notice(command, "aichat GPT disabled")
    return removed


# aichat command
@add_typing_command_response
async def switch(command: Command):
    """
    Enable or disable aichat GPT
    :param command:
    :return:
    """

    # if existing hook (room was activated before)
    if is_aichat_active_in_current_room(command):
        await deactivate_aichat_in_current_room(command)
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
        await activate_aichat_in_current_room(command, model_name)


# Not every message to the room actually triggers bot to start typing!!!
# aichat hook
async def send_message_to_openai_gpt(client: AsyncClient, room_id: str, event: RoomMessageText):
    """
    Send a received message to aichat gpt if hook is active on room
    :param client:
    :param room_id:
    :param event:
    :return:
    """
    # if allowed rooms is empty or room is in allowed rooms
    if plugin.read_config("allowed_rooms") == [] or room_id in plugin.read_config("allowed_rooms"):
        nr_of_users_in_room = get_nr_of_users_in_room_from_client(client, room_id)
        we_are_in_a_private_room: bool = nr_of_users_in_room == 2
        # we are not in a private room
        # check if bot username was mentioned
        # client.user_id = @<username>:<matrix-home-server-domain>
        simple_client_id: str = await get_bot_client_id(client)
        # message does not include relates_to quote parts "> text"
        # -> client ID must always be included in latest message itself!
        message = remove_lines_with_answer_character(event.body)
        if we_are_in_a_private_room or simple_client_id in message:
            await client.room_typing(room_id, timeout=TYPING_TIMEOUT_DEFAULT)
            # bot was mentioned
            room_db: ROOM_DB_TYPE = await get_room_db_from_room_id(room_id)  # can return empty dict
            if not room_db:  # empty dict is False
                await plugin.send_notice(client, room_id, f"No data found for this room, disabling hook...")
                plugin.del_hook("m.room.message", send_message_to_openai_gpt, room_id_list=[room_id])
                return
            # prepare config

            def get_db_value_or_config(key_db: str, key_config: str) -> any:
                return room_db.get(key_db, plugin.read_config(key_config))

            model_name: str = get_db_value_or_config("model_name", "default_model")
            message_history_len: int = get_db_value_or_config("message_history_len", "default_message_history_len")
            system_role_content: str = get_db_value_or_config("system_role_content", "default_system_role_content")
            max_tokens: int = plugin.read_config("max_tokens")
            openai.api_key = plugin.read_config("openai_api_key")
            logger.debug(f"{model_name}, {message_history_len}, {max_tokens}")
            # prepare messages send to openai
            aichat = AiMessages(system_role_content=system_role_content,
                                assistant_client_id=simple_client_id)
            aichat.append_user_message(message)
            if event.source['content'].get('m.relates_to', False):
                # current message relates to a previous message
                # we will not take into account any message history besides related message
                relates_to: RoomContextResponse | RoomContextError = await client.room_context(
                    room_id=room_id, event_id=event.source['content']['m.relates_to']['m.in_reply_to']['event_id'],
                    limit=1)
                relates_to_sender_id = relates_to.event.sender
                relates_to_message = relates_to.event.body  # is actually event of type RoomMessageFormatted
                aichat.insert_related_message_as_context(source_client_id=relates_to_sender_id,
                                                         content=relates_to_message)
            elif message_history_len > 0:
                nr_history_messages_found = 0
                current_event_id = event.event_id
                while nr_history_messages_found < message_history_len:
                    # limit = 2 because it searches forwards and backwards (half of the limit)
                    relates_to: RoomContextResponse = await client.room_context(
                        room_id=room_id, event_id=current_event_id, limit=2)
                    event_before = relates_to.events_before[0]
                    current_event_id = event_before.event_id
                    if isinstance(event_before, RoomMessageText):
                        # found a message
                        nr_history_messages_found += 1
                        aichat.insert_related_message_as_context(event_before.sender, event_before.body)
                        logger.debug(f"old message found: {event_before.body}")
            # # send feedback reaction
            # await plugin.send_reaction(client, room_id, event.event_id, REACTION_SUCCESS)
            try:
                response = await openai.ChatCompletion.acreate(
                    model=model_name,
                    max_tokens=max_tokens,
                    messages=aichat.messages
                )
                answer = response['choices'][0]['message']['content']
                # finish_reason: str = response['choices'][0]['finish_reason']
                # tokens_spend = response['usage']['total_tokens']
                # expanded_message = f"Response info: {model_name}, {finish_reason},  tokens spend [{tokens_spend}]"
                await plugin.send_message(client, room_id, answer)
            except openai.error.OpenAIError as e:
                logger.exception(e)
                await plugin.send_notice(client, room_id, f"OpenAI Error: {e}")
        await client.room_typing(room_id, typing_state=False)
        return


async def hook_member(client, room_id, event: RoomMemberEvent):
    if event.membership == "join" and event.prev_membership == "join":
        # most likely avatar was changed, ignore this case!
        return
    # "invite" triggered before get_how_to_interact_with_aichat_message recognizes a joined user
    # "join" is triggered on avatar change!
    if event.membership in ("join", "leave", "ban"):
        # number of members has changed, update usage info!
        usage_info = await get_how_to_interact_with_aichat_message(client, room_id)
        await plugin.send_notice(client, room_id, usage_info)


def remove_lines_with_answer_character(string):
    lines = string.split("\n")
    new_lines = []
    for line in lines:
        if line and line[0] != ANSWER_CHARACTER:
            new_lines.append(line)
    return "\n".join(new_lines)


def remove_trailing_bot_name(message: str, bot_name) -> str:
    split_message = message.split(" ", 1)
    first_word = split_message[0]
    if bot_name in first_word and len(split_message) == 2:  # some clients will reference the bot like: `@bot-name: `
        return split_message[1]  # rest of the message (not split)
    else:
        return message


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
            content = remove_trailing_bot_name(content, self.assistant_client_id)
        self.messages.insert(1, new_ai_message(role=role, content=content))

    def append_user_message(self, content: str):
        clean_content = remove_trailing_bot_name(content, self.assistant_client_id)
        self.append_message(role="user", content=clean_content)


setup()
