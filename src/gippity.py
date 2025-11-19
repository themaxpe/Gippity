import discord
from discord.ext import commands
import datetime
import sqlite3
import asyncio

class Gippity(commands.Bot):

    # Override commands.Bot setup hook to allow for extra data to load before setup
    async def setup_hook(self):
        print("Hello")
        await self.load_configs()
    
    ###################
    # SETUP FUNCTIONS #
    ###################
    
    # Used to load guild and channel config
    async def load_configs(self):
        print("Connecting to config database")
        
        self._configdb = sqlite3.connect("config.db")
        self._configcursor = self._configdb.cursor()

        self._configcursor.execute("""CREATE TABLE IF NOT EXISTS config (
        ENTRY_ID INTEGER IDENTITY(1, 1) PRIMARY KEY,
        OBJECT_ID INTEGER,
        OBJECT_TYPE TEXT,
        KEY TEXT,
        KEY_VALUE TEXT
        );""")

        print("Loading guild and channel configs to memory")
    


        # Store configs into memory
        self._guild_config = {}
    
    # Load a specific guild config
    # Assumes self.load_configs() has executed successfully, and connected to db
    async def load_config_for_guild(self, guild: discord.Guild):
       
        # guild_config[guildid] will hold all config data relevant to guild
        # "channels" and "global" distinguish between individual channel config and guild-wide config
        self._guild_config[guild.id] = {"channels":{}, "global":{}}                

    ##################
    # CONFIG METHODS #
    ##################

    async def addConfigToObject(self, discordObject, option, config):
        

        # First get old config
        newConfig = await self.getObjectConfigOption(discordObject, option)
        if newConfig is None:

            # No need to worry about 
            if option in ["instructions"]:
                config = [config]

            newConfig = config

        elif option in ["instructions"]:
            newConfig.append(config)

        else:
            newConfig = config
        

    
        if type(discordObject) == discord.Guild:

            # If guild global config not loaded
            if discordObject.id not in self._guild_config:
                # Load it!
                await self.load_config_for_guild(discordObject)

            self._guild_config[discordObject.id]["global"][option] = newConfig


        elif type(discordObject) == discord.TextChannel:
            
            # If guild hasn't been loaded yet (somehow)
            if discordObject.guild.id not in self._guild_config:
                # Load it
                await self.load_config_for_guild(discordObject.guild)

            # If channel not yet configured
            if discordObject.id not in self._guild_config[discordObject.guild.id]["channels"]:
                # Create empty dict for it
                self._guild_config[discordObject.guild.id]["channels"][discordObject.id] = {}

            # Finally set key
            self._guild_config[discordObject.guild.id]["channels"][discordObject.id][option] = newConfig

        else:
            return False

        return True

    async def getObjectConfig(self, discordObject):
        
        if type(discordObject) == discord.Guild:
            if discordObject.id in self._guild_config:
                return self._guild_config[discordObject.id]["global"]
                                            
        elif type(discordObject) == discord.TextChannel:
            # If channel guild is configured
            if discordObject.guild.id in self._guild_config:
                # If channel is configured within said guild
                if discordObject.id in self._guild_config[discordObject.guild.id]["channels"]:
                    return self._guild_config[discordObject.guild.id]["channels"][discordObject.id]

        return None 

    async def getObjectConfigOption(self, discordObject, option):
        
        objectConfig = await self.getObjectConfig(discordObject)
        if objectConfig is not None:
            if option in objectConfig:
                return objectConfig[option]
        
        return None


    ######################
    # CORE FUNCTIONALITY #
    ######################

    # Used to get instructions from added context
    # Modify to customise instructions GLOBALLY
    # Some options can be passed to msg_ctx to customise certain parameters per guild
    async def genInstructions(self, msg_ctx: dict = {}):
        instructions = "You are a British human on the platform Discord. Your name is Gippity. "
        instructions += "When speaking English, make sure to always use British English unless explicitly asked otherwise. "
        instructions += "You can tag a user by using <@USERID> where USERID is the number associated with their account. "
        
        if "previous_messages" in msg_ctx:
            instructions += f"Provided is a list of previous messages for added context: {msg_ctx['previous_messages']}. " 
        
        if "author" in msg_ctx:
            instructions += f"The current message was sent by User {msg_ctx['author'].id} (username: {msg_ctx['author'].name}). "
            if msg_ctx["author"].global_name:
                instructions += f"The User currently has the nickname {msg_ctx['author'].global_name} this guild."

        if "datetime" in msg_ctx:
            time, date = self.formatTime(msg_ctx["datetime"])
            instructions += f"The current message was sent at {time} on {date}. "

        if "referenced_msg" in msg_ctx:
            message_content = await self.getMessageFromReference(msg_ctx["referenced_msg"])

            instructions += f"The user is directly referencing the message with id '{msg_ctx['referenced_msg'].message_id}'."
            if message_content:
                instructions += f"The text content of the referenced message is: {message_content.content}"

        if "guild" in msg_ctx:
            instructions += f"The current message was sent in a guild named {msg_ctx['guild'].name}."
            
            nick = msg_ctx["guild"].me.nick
            if nick:
                instructions += f"Your current nickname in this guild is {nick}."
            else:
                instructions += f"You have no nickname in this guild."
            

        return instructions


    # Handles actually generating instructions from message
    # Use this instead of genInstructions if you don't need raw control over every argument
    async def genInstructionsFromMessage(self, message: discord.Message, msg_ctx: dict = {}):

        print("Generating Instruction Set")

        if "previous_messages" not in msg_ctx:
            print("Previous Messages not provided, generating own")
            previous_messages = [msg async for msg in message.channel.history(limit=51)][::-1][:-1]

            msg_ctx["previous_messages"] = list(map(self.formatMessage, previous_messages))
        
        print(msg_ctx["previous_messages"])

        msg_ctx["author"] = message.author
        msg_ctx["datetime"] = message.created_at

        if message.guild:
            msg_ctx["guild"] = message.guild
        
        if message.reference:
            msg_ctx["referenced_msg"] = message.reference

        instructions = await self.genInstructions(msg_ctx)
            
        guildInstructions = await self.getObjectConfigOption(message.guild, "instruction")
        channelInstructions = await self.getObjectConfigOption(message.channel, "instruction")

        if guildInstructions is not None:
            instructions += guildInstructions

        if channelInstructions is not None:
            instructions += channelInstructions

        return instructions

    async def getMessageFromReference(self, msg: discord.MessageReference) -> discord.Message:
        if msg.cached_message:
            return msg.cached_message

        channel = await self.fetch_channel(msg.channel_id)
        await asyncio.sleep(0.1)
        if channel:
            newMsg = await channel.fetch_message(msg.message_id)
            return newMsg

    ####################
    # HELPER FUNCTIONS #
    ####################

    # Format message time to standard format
    def formatTime(self, sent: datetime.datetime):

        time = f"{sent.hour}:{sent.minute} UTC"
        date = f"{sent.day}-{sent.month}-{sent.year}"
    
        return time, date

    # Format message for message list
    def formatMessage(self, message: discord.Message):

        _sent = message.created_at
        time, date = self.formatTime(_sent)

        user = ""
        if message.author == self.user:
            user = "You"
        else:
            user = f"User {message.author.id} (username: {message.author.name})"

        msgString = f"At {time} on {date}, {user} said (messageID: {message.id}): {message.content}"

        return msgString
