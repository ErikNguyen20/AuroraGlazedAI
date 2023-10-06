import re
from typing import Optional, List

import discord
from discord.ext import commands
import os
import json
import asyncio
from queue import SimpleQueue
import random

from utils.LLM import LLM


class BotDataManager:
    DEFAULT_ROLE = "You are trying to blend in with a group of young people without being ousted as a robot. You are currently on the social media platform Discord. Converse as naturally as possible."

    DEFAULT_BOT_DIRECTIVES_PATH = "bot_directives"
    SERVER_DATA_FILE_PATH = "server_data"
    ROLES_FILES_PATH = "roles"
    DEFAULT_ROLE_FILE_NAME = "default_role.txt"

    MESSAGE_CACHE_FILE_NAME = "message_cache.json"
    METADATA_FILE_NAME = "metadata.json"

    def __init__(self, bot_directives_path: str = DEFAULT_BOT_DIRECTIVES_PATH):
        # TServer_ID(str): {"role": "default_role.txt", ...}(dict)
        self.metadata = {}
        # TServer_ID(str): [{"role": "user", "content": ""},{...},...](list)
        self.messages = {}
        # TServer_ID(str): system message(str)
        self.roles = {}

        # Sets up internal file directory
        if not os.path.exists(bot_directives_path):
            os.makedirs(BotDataManager.DEFAULT_BOT_DIRECTIVES_PATH)
        self.directives_path = bot_directives_path

        # Sets up the roles file directory
        if not os.path.exists(os.path.join(self.directives_path, BotDataManager.ROLES_FILES_PATH)):
            os.makedirs(os.path.join(self.directives_path, BotDataManager.ROLES_FILES_PATH))
        self.roles_data_path = os.path.join(self.directives_path, BotDataManager.ROLES_FILES_PATH)

        # Initializes the default role of the bot
        if not os.path.exists(os.path.join(self.roles_data_path, BotDataManager.DEFAULT_ROLE_FILE_NAME)):
            with open(os.path.join(self.roles_data_path, BotDataManager.DEFAULT_ROLE_FILE_NAME), "w") as file:
                file.write(BotDataManager.DEFAULT_ROLE)

        # Sets up server data directory
        if not os.path.exists(os.path.join(self.directives_path, BotDataManager.SERVER_DATA_FILE_PATH)):
            os.makedirs(os.path.join(self.directives_path, BotDataManager.SERVER_DATA_FILE_PATH))
        self.server_data_path = os.path.join(self.directives_path, BotDataManager.SERVER_DATA_FILE_PATH)

        # Loads data from file directory
        self.load_server_data()

    def initialize_default_server_data(self, server_folder: str):
        # Initialize default values if not found
        if server_folder not in self.metadata:
            self.metadata[server_folder] = {}
            self.metadata[server_folder]["selected_role"] = BotDataManager.DEFAULT_ROLE_FILE_NAME
            self.roles[server_folder] = self.get_role_data(self.metadata[server_folder]["selected_role"])
        if server_folder not in self.messages:
            self.messages[server_folder] = []

    def load_server_data(self):
        for server_folder in os.listdir(self.server_data_path):
            # Read stored data files within the server_folder
            for name in os.listdir(os.path.join(self.server_data_path, server_folder)):
                read_data = None
                with open(os.path.join(self.server_data_path, server_folder, name), "r") as json_file:
                    # Read and parse data from the file
                    try:
                        read_data = json.load(json_file)
                    except Exception as e:
                        print(f"[ERROR] Failed to read in json file \"{name}\" {str(e)}")
                    finally:
                        json_file.close()

                    # Updates the data from file
                    if name == BotDataManager.MESSAGE_CACHE_FILE_NAME:
                        self.messages[server_folder] = read_data if read_data is not None else []
                    elif name == BotDataManager.METADATA_FILE_NAME:
                        self.metadata[server_folder] = read_data if read_data is not None else {}
                        if "selected_role" not in self.metadata[server_folder]:
                            self.metadata[server_folder]["selected_role"] = BotDataManager.DEFAULT_ROLE_FILE_NAME
                        self.roles[server_folder] = self.get_role_data(self.metadata[server_folder]["selected_role"])

            # Initialize default values if not found
            self.initialize_default_server_data(server_folder)

    def get_role_data(self, file_name: str) -> str:
        # Gets the role string from the file
        if os.path.exists(os.path.join(self.roles_data_path, file_name)):
            with open(os.path.join(self.roles_data_path, file_name), "r") as file:
                return file.read()
        elif file_name != BotDataManager.DEFAULT_ROLE_FILE_NAME:
            return self.get_role_data(BotDataManager.DEFAULT_ROLE_FILE_NAME)
        else:
            return BotDataManager.DEFAULT_ROLE

    def update_metadata_file(self, server_folder: str):
        # If server folder hasn't been created yet, create one.
        if not os.path.exists(os.path.join(self.server_data_path, server_folder)):
            os.mkdir(os.path.join(self.server_data_path, server_folder))

        # Writes metadata to server folder
        with open(os.path.join(self.server_data_path, server_folder, BotDataManager.METADATA_FILE_NAME),
                  "w") as json_file:
            json.dump(self.metadata[server_folder], json_file, indent=4)
            json_file.close()

    def update_messages_file(self, server_folder: str):
        # If server folder hasn't been created yet, create one.
        if not os.path.exists(os.path.join(self.server_data_path, server_folder)):
            os.mkdir(os.path.join(self.server_data_path, server_folder))

        # Writes messages history to server folder
        with open(os.path.join(self.server_data_path, server_folder, BotDataManager.MESSAGE_CACHE_FILE_NAME),
                  "w") as json_file:
            json.dump(self.messages[server_folder], json_file, indent=4)
            json_file.close()

    def init_source_server_folder(self, server_folder: str):
        # Initializes variables
        if server_folder not in self.messages:
            self.messages[server_folder] = []
        if server_folder not in self.metadata:
            self.metadata[server_folder] = {}
            self.metadata[server_folder]["selected_role"] = BotDataManager.DEFAULT_ROLE_FILE_NAME
            self.roles[server_folder] = self.get_role_data(self.metadata[server_folder]["selected_role"])
            self.update_metadata_file(server_folder)

    def switch_selected_role(self, server_folder: str, role_file: str):
        if server_folder not in self.metadata:
            self.metadata[server_folder] = {}

        # Updates role based on the file
        if not role_file.endswith(".txt"):
            role_file = role_file + ".txt"
        if os.path.exists(os.path.join(self.roles_data_path, role_file)):
            # Check if the role file has already been selected.
            if role_file == self.metadata[server_folder]["selected_role"]:
                return True

            self.metadata[server_folder]["selected_role"] = role_file
            self.roles[server_folder] = self.get_role_data(self.metadata[server_folder]["selected_role"])
            self.update_metadata_file(server_folder)
        else:
            return False

        # Returns true if successful
        return True

    # Gets list of available roles
    def get_list_of_roles(self) -> List[str]:
        return os.listdir(self.roles_data_path)

    # DiscordBot Integration
    def message_source_to_server_folder(self, message: discord.Message) -> str:
        # Creates a unique "key" based on the source of the message
        if isinstance(message.channel, discord.DMChannel):
            return "dm_" + str(message.author.id)
        else:
            return "guild_" + str(message.guild.id)

    async def download_personality_from_attachment(self, attachment: discord.Attachment) -> bool:
        # Downloads a txt personality file into the roles directory
        try:
            await attachment.save(fp=os.path.join(self.roles_data_path, attachment.filename))
        except Exception as e:
            print(f"[ERROR] Failed to download personality file. {str(e)}")
            return False
        return True


class DiscordBot:
    COMMAND_PERMISSION_ROLE = "bothandler"
    COMMAND_PREFIX = "$"
    DEVELOPER_PORTAL_WEBSITE = "https://discord.com/developers/applications"

    def __init__(self, DISCORD_TOKEN: str, OWNER_ID: Optional[int],
                 bot_directives_path: str = BotDataManager.DEFAULT_BOT_DIRECTIVES_PATH):
        # Sets up discord integration
        self.DISCORD_TOKEN = DISCORD_TOKEN

        intents = discord.Intents.default()
        intents.message_content = True
        self.client: commands.Bot = commands.Bot(command_prefix=DiscordBot.COMMAND_PREFIX, intents=intents)
        self.client.owner_id = OWNER_ID
        self.commands = {}
        self.help_command = None

        # Instantiate Data Manager and LLM
        self.Data = BotDataManager(bot_directives_path)
        self.LLM = LLM()

        # Messages Processing Queue
        self.processing_queue = SimpleQueue()
        self.in_queue_set = set()

    def sanitize_username(self, username: str, allow_spaces=True) -> str:
        # Removes all characters except for alphanumeric and some symbols
        username = re.sub(r'[^a-zA-Z0-9_]', '', username)
        if not allow_spaces:
            username = username.replace(' ', '')
        return username

    def sanitize_message_content(self, message: discord.Message) -> str:
        content = message.content
        # Formats the mentions in message to be readable with usernames instead of id
        for mention in message.mentions:
            if mention.id == self.client.user.id:
                # Removes mention of the bot itself from the message
                content = message.content.replace(f'<@{mention.id}>', '')
            else:
                display_name = self.sanitize_username(mention.display_name, allow_spaces=False)
                content = message.content.replace(f'<@{mention.id}>', f'<@{display_name}>')

        return content

    def sanitize_bot_response(self, response: str) -> str:
        # Removes the profile header string '[USERNAME]' from response
        if response.find(':') != -1:
            response = re.sub(r'^\[[^]]+]:\s*', '', response)
        else:
            response = re.sub(r'^\[[^]]+]\s*', '', response)

        # Converts mention <@USERNAME> to USERNAME
        response = re.sub(r'<@(.*?)>', lambda match: match.group(1), response)
        return response

    def execute_actions_in_bot_response(self, response):
        # Inserts pictures, adds reactions, etc based on searchable tokens. ex: '@{PICTURE OF DEER}'
        pass

    def add_role_contexts(self, server_folder: str, message: discord.Message) -> str:
        role = self.Data.roles[server_folder]
        # Adds context to system role from embedding extraction (pdf search)
        return role

    async def generate_conversation_response(self, message: discord.Message):
        # Get the unique server identifier for the message source
        server_folder = self.Data.message_source_to_server_folder(message)
        self.Data.init_source_server_folder(server_folder)

        # Processes the content of the message for the LLM
        user_message = self.sanitize_message_content(message)
        print(f"\n[SERVICING {server_folder}]")  # Prints Server ID
        print("INPUT: ", user_message)  # Prints Prompt
        user_message = {"role": "user", "content": f"[{self.sanitize_username(message.author.display_name)}]: {user_message}"}

        # Process and add context to the system role
        context_added_role = self.add_role_contexts(server_folder, message)
        system_role = {"role": "system", "content": context_added_role}

        # Prompt Message
        prompt_messages = [system_role] + self.Data.messages[server_folder] + [user_message]


        # Ensures that the token limit isn't reached
        while self.LLM.compute_messages_token_count(prompt_messages) > LLM.TOKEN_COUNT_THRESHOLD:
            prompt_messages.pop(1)

        # Generate Conversation Response from the LLM
        response = await self.LLM.LLM_get_response(prompt_messages)
        if response is None:
            print("[ERROR] Bot Failed to generate response!")
            return
        print("OUTPUT: ", response)  # Print Response

        # If there are actions specified, execute them.
        self.execute_actions_in_bot_response(response)

        # Adds bot response to messages. Ensures that the token limit isn't reached
        prompt_messages.append({"role": "assistant", "content": self.sanitize_bot_response(response)})
        while self.LLM.compute_messages_token_count(prompt_messages) > LLM.TOKEN_COUNT_THRESHOLD:
            prompt_messages.pop(1)

        # Updates the message history
        self.Data.messages[server_folder] = prompt_messages[1:]
        self.Data.update_messages_file(server_folder)

        # Sends the response to discord
        await self.send_message(message_info=message, response=self.sanitize_bot_response(response), ref=message)

    # Sends message to the user to whatever channel they are in. Optionally, perform a reply.
    async def send_message(self, message_info: discord.Message, response: str, ref: Optional[discord.Message] = None):
        try:
            if isinstance(message_info.channel, discord.DMChannel):
                # Send to DMs
                await message_info.author.send(response, reference=ref)
            else:
                # Send to public channel
                await message_info.channel.send(response, reference=ref)
        except Exception as e:
            print(f"[ERROR] Failed to send message. {str(e)}")

    # Function that registers commands to the bot
    def add_command(self, command: callable, perm_level: int, description: Optional[str] = None):
        self.commands[command.__name__] = (command, perm_level, description)

    # Helper function that checks for permission level
    def permission_allowed(self, message: discord.Message, perm_level: int):
        if perm_level == 0:
            return True
        elif perm_level == 1:
            # Owner of the server has permission
            if message.guild and message.guild.owner_id == message.author.id:
                return True
            # Owner of the bot has permission
            if message.author.id == self.client.owner_id:
                return True
            # Anyone with the specific role
            if hasattr(message.author, "roles") and message.author.roles is not None:
                return any(
                    role.name.lower() == DiscordBot.COMMAND_PERMISSION_ROLE.lower() for role in message.author.roles)
        elif perm_level == 2:
            # Owner of the bot has permission
            if message.author.id == self.client.owner_id:
                return True

        return False

    # Processes the message (generates a response)
    async def process_message(self, message: discord.Message):
        # Generates response
        inference_task = asyncio.create_task(self.generate_conversation_response(message))

        # Gives random delay to then start typing indicator
        await asyncio.sleep(random.uniform(2, 5))

        # Starts typing indicator if the task is not done.
        async with message.channel.typing():
            await inference_task

    # Loops indefinitely. Called when the bot is in an on_ready state
    async def loop(self):
        while True:
            # Repeatedly processes messages from users one at a time.
            if not self.processing_queue.empty():
                message = self.processing_queue.get()
                self.in_queue_set.remove(message.author.id)
                await self.process_message(message)
            else:
                await asyncio.sleep(0.2)

    def run(self):

        # ========================================= #
        #               Client Events
        # ========================================= #
        @self.client.event
        async def on_ready():
            print(f'[SYSTEM] {self.client.user.display_name} has connected to Discord!')
            if self.help_command is not None:
                print(f'[SYSTEM] Use {DiscordBot.COMMAND_PREFIX}{self.help_command.__name__} for information.')
            print(f'[SYSTEM] Developer Portal: {DiscordBot.DEVELOPER_PORTAL_WEBSITE}')

            # Initializations
            await self.client.change_presence(status=discord.Status.online)

            # Runs processing loop
            await self.loop()

        @self.client.event
        async def on_message(message: discord.Message):
            # Ensures that event only triggers on messages not generated by itself
            if message.author == self.client.user:
                return

            # Ignores certain types of messages and ignores from other bots
            if message.stickers or message.author.bot:
                return

            # Only responds when replied to or mentioned
            if (isinstance(message.channel, discord.TextChannel) and not self.client.user.mentioned_in(message) and not
            (
                    message.reference and message.reference.cached_message and message.reference.cached_message.author == self.client.user)):
                return

            # Processes Bot Commands
            if message.content.startswith(DiscordBot.COMMAND_PREFIX):
                await on_command(message)
                return

            # Adds message to processing queue only if user does not have a request in queue
            if message.author.id in self.in_queue_set:
                return
            self.in_queue_set.add(message.author.id)
            self.processing_queue.put(message)

        # ========================================= #
        #               Bot Commands
        # ========================================= #

        # Runs when a command is executed
        async def on_command(message: discord.Message):
            # Separates arguments in the command
            args = message.content.split(' ')
            if args is None or len(args) == 0:
                return

            # Calls function if the command was added
            args[0] = args[0][1:]
            if args[0] in self.commands:
                if self.permission_allowed(message, self.commands[args[0]][1]):
                    await self.commands[args[0]][0](message)
                else:
                    await self.send_message(message, "You do not have the required permissions to run this command.",message)
            elif self.help_command is not None:
                # Unknown command message, lets the user know about the help command
                await self.send_message(message, f"Unknown Command. Use {DiscordBot.COMMAND_PREFIX}{self.help_command.__name__} for more.", message)
            else:
                await self.send_message(message, f"Unknown Command.", message)

        # Switch Personality Command
        async def switch_personality(message: discord.Message):
            # Ensures that there are exactly 2 arguments
            args = message.content.split(' ')
            if len(args) != 2:
                await self.send_message(message, f"Invalid argument syntax.", message)
                return

            # Result if the personality sucessfully switched
            result = self.Data.switch_selected_role(self.Data.message_source_to_server_folder(message), args[1])
            if result:
                await self.send_message(message, f"Personality switched to {args[1]}.", message)
            else:
                await self.send_message(message, f"Something went wrong or {args[1]} does not exist.", message)

        # List personalities Command
        async def list_personalities(message: discord.Message):
            list_message = "List of Personalities: "
            for role in self.Data.get_list_of_roles():
                list_message += f" ***{role}*** "
            await self.send_message(message, list_message, message)

        # Add personality Command
        async def add_personality(message: discord.Message):
            if message.attachments is None or len(message.attachments) == 0:
                await self.send_message(message, f"Please attach a .txt file to the message.", message)
                return
            attachment = message.attachments[0]
            if attachment is not None and attachment.filename.endswith(".txt"):
                # Ensure that personality file does not already exist
                if attachment.filename in self.Data.get_list_of_roles():
                    await self.send_message(message, f"Personality {attachment.filename} already exists!", message)
                    return

                # Download personality file into the directory
                result = await self.Data.download_personality_from_attachment(attachment)
                if result:
                    await self.send_message(message, f"Personality {attachment.filename} added!", message)
                else:
                    await self.send_message(message, f"Failed to download {attachment.filename}.", message)
            else:
                await self.send_message(message, f"Invalid attachment type! Please attach a .txt file to the message.",
                                        message)

        # Clear History Command
        async def clear_history(message: discord.Message):
            server_folder = self.Data.message_source_to_server_folder(message)
            self.Data.messages[server_folder] = []
            self.Data.update_messages_file(server_folder)
            await self.send_message(message, f"History Cleared!", message)

        async def nickname(message: discord.Message):
            # Ensures that there is more than 1 argument
            args = message.content.split(' ')
            if len(args) < 2:
                await self.send_message(message, f"Invalid argument syntax.", message)
                return

            # Ensure that the command is only being run on a public server channel
            if message.guild is None:
                await self.send_message(message, f"Cannot change nickname in this channel.", message)
                return

            # Edit the nickname
            try:
                await message.guild.get_member(self.client.user.id).edit(nick=' '.join(args[1:]))
            except Exception as e:
                await self.send_message(message, f"Failed to change nickname.", message)
                print(f"[ERROR] Failed to change nickname {str(e)}")
                return
            await self.send_message(message, f"Nickname changed successfully!", message)

        # Personality Info Command
        async def personality_info(message: discord.Message):
            # Ensures that there are exactly 2 arguments
            args = message.content.split(' ')
            if len(args) == 1:
                # If no role is specified, just display for the selected role
                server_folder = self.Data.message_source_to_server_folder(message)
                if server_folder in self.Data.roles:
                    await self.send_message(message, f"```\n{self.Data.roles[server_folder]}```", message)
                else:
                    await self.send_message(message, f"Role does not exist.", message)
                return
            elif len(args) != 2:
                await self.send_message(message, f"Invalid argument syntax.", message)
                return

            # Checks if the role exists in the directory
            if args[1] not in self.Data.get_list_of_roles():
                await self.send_message(message, f"{args[1]} does not exist.", message)
                return
            await self.send_message(message, f"```\n{self.Data.get_role_data(args[1])}```", message)

        # Bot Info Command
        async def bot_info(message: discord.Message):
            server_folder = self.Data.message_source_to_server_folder(message)
            if server_folder not in self.Data.metadata:
                await self.send_message(message, "No data found for this bot.", message)
                return

            # Prints out information
            info_message = "```\nBot Information:\n"
            info_message += "\nserver_id: " + server_folder
            for key, value in self.Data.metadata[server_folder].items():
                info_message += "\n" + key + ": " + str(value)
            await self.send_message(message, info_message + "```", message)

        # Help Command
        async def help_commands(message: discord.Message):
            help_message = "```\nList of Commands:\n"
            for key, value in self.commands.items():
                description = value[2] if value[2] is not None else ""
                help_message += "\n" + DiscordBot.COMMAND_PREFIX + key + description
            await self.send_message(message, help_message + "```", message)

        # ========================================= #
        #              Runs Discord Bot
        # ========================================= #

        # Adds commands to the bot
        self.add_command(switch_personality, 1, " [role_file.txt] - Switches personality of bot")
        self.add_command(list_personalities, 1, " - List available personalities")
        self.add_command(add_personality, 2, " <ATTACH .TXT FILE> - Adds a personality to the bot")
        self.add_command(personality_info, 0, " [role_file.txt] - Gets the personality data")
        self.add_command(clear_history, 1, " - Clears local chat history")
        self.add_command(bot_info, 0, " - Gets the current server's bot information")
        self.add_command(nickname, 1, " [nickname] - Sets the nickname of the bot")
        self.add_command(help_commands, 0, " - Gets list of commands and information")
        self.help_command = help_commands

        # Runs loop for bot
        self.client.run(self.DISCORD_TOKEN)
