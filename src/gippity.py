import discord
from discord.ext import commands
import datetime
import sqlite3
import asyncio
import random
import string

class Gippity(commands.Bot):

    # Override commands.Bot setup hook to allow for extra data to load before setup
    async def setup_hook(self):
        print("Hello")
        self.configParams = {
            "listEntry":["instruction"] # All config options which can have multiple values go here
        }
        await self.load_configs()
    
        

    ###################
    # SETUP FUNCTIONS #
    ###################
    
    # Used to load guild and channel config
    async def load_configs(self):
        print("Connecting to config database")
        
        self.connect_to_db("config.db")

        self._configcursor.execute("""CREATE TABLE IF NOT EXISTS config (
        ENTRY_ID CHAR(32) PRIMARY KEY,
        OBJECT_ID INTEGER,
        OBJECT_TYPE VARCHAR(16),
        KEY VARCHAR(32),
        KEY_VALUE TEXT,
        TIME_ADDED TIMESTAMP
        );""")

        # Store configs into memory
        self._guild_config = {}
        
    
    def connect_to_db(self, db):
        self._configdb = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
        self._configcursor = self._configdb.cursor()

    # Load a specific guild config
    # Assumes self.load_configs() has executed successfully, and connected to db
    async def load_config_for_guild(self, guild: discord.Guild):
        
        print(f"Loading config for guild {guild}")
        
        

        # guild_config[guildid] will hold all config data relevant to guild
        # "channels" and "global" distinguish between individual channel config and guild-wide config
        self._guild_config[guild.id] = {"channels":{}, "global":{}}
        
        print("Querying Database")
        existingConfig = self._configcursor.execute("SELECT ENTRY_ID,KEY,KEY_VALUE,TIME_ADDED FROM config WHERE OBJECT_ID = ?", (guild.id,)).fetchall()
        
        
        print(existingConfig)
        # Add item to guild config
        for entryID,key,value,_ in sorted(existingConfig, key=lambda x: x[3]):
             
            if key in self.configParams["listEntry"]:
                if key not in self._guild_config[guild.id]["global"]:
                    self._guild_config[guild.id]["global"][key] = [(value, entryID)]
                else:
                    self._guild_config[guild.id]["global"][key].append((value, entryID))
            else:
                self._guild_config[guild.id]["global"][key] = (value, entryID)

    async def load_config_for_channel(self, channel: discord.Channel):

        pass


    async def write_config_change(self, object, key: str, option: str, value = None, entryID = None):
        print("Writing Config")
        objectType = "channel"
        if type(object) == discord.Guild:
            objectType = "guild"
        match option:
            case "add":
                print("Adding Config to DB")
                
                print(object)
                print(key)
                print(option)
                print(value)
               
                print(entryID)

                if type(value) == list:
                    print("Value is list")
                    value = value[0] # For now should be just one item *anyway*
                    #TODO: Add support for multiple values

                if key in self.configParams["listEntry"]:
                    
                    print("Adding Instruction to DB")
                    self._configcursor.execute("""INSERT INTO config(ENTRY_ID,OBJECT_ID,OBJECT_TYPE,KEY,KEY_VALUE,TIME_ADDED) VALUES(?, ?, ?, ?, ?, ?)""", (entryID,object.id,objectType,key,value,datetime.datetime.now(),))
                else:
                    if len(self._configcursor.execute("SELECT * FROM config WHERE OBJECT_ID = ? AND KEY = ?;", (object.id, key,)).fetchall()) > 0:
                        self._configcursor.execute("UPDATE config SET KEY_VALUE = ? WHERE OBJECT_ID = ? AND KEY = ?;", (value, object.id, key,))
                    else:
                        self._configcursor.execute("""INSERT INTO config(ENTRY_ID,OBJECT_ID,OBJECT_TYPE,KEY,KEY_VALUE,TIME_ADDED) VALUES(?, ?, ?, ?, ?, ?)""", (entryID,object.id,objectType,key,value,datetime.datetime.now(),))
            case "remove":
                if key in self.configParams["listEntry"]:
                    if value is None:
                        return
                    
                    # Get entry ID
                    if not entryID:
                        objectConfig = await self.getObjectConfigOption(object, key)
                        if objectConfig is None:
                            print("Empty config returned on remove request")
                            return

                        entryID = objectConfig[value][1]
                    #print(objectConfigID)
                    self._configcursor.execute("""DELETE FROM config WHERE ENTRY_ID=?""", (entryID,))
                print("Removing config from DB")

        self._configdb.commit()

    ##################
    # CONFIG METHODS #
    ##################

    async def addConfigToObject(self, discordObject, option, config):
        
        entryID = self.semirandomString() # Yes, ID *should* be hashed in some form to guaruntee uniqueness. This is good enough for now give me a break :)
        # First get old config
        newConfig = await self.getObjectConfigOption(discordObject, option)
        if newConfig is None:

            # No need to worry about 
            if option in self.configParams["listEntry"]:
                newConfig = [(config, entryID)]
            else:
                newConfig = (config, entryID)

        elif option in self.configParams["listEntry"]:
            newConfig.append((config, entryID))

        else:
            newConfig = (config, entryID)
        

    
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

        await self.write_config_change(discordObject, option, "add", config, entryID)
        return True

    async def removeConfigFromObject(self, discordObject, option, config = None) -> bool:
        currentConfig = await self.getObjectConfigOption(discordObject, option)
        if currentConfig is None:
            print("No existing config, just skip I guess")
            return True # Need to return message to user

        if option in self.configParams["listEntry"]:
            if config is None:
                print("No config provided")
                return False
            try:
                config = int(config)
                config -= 1 # Adjust for 0-indexing
            except:
                print("Config provided is not of type int")
                return False

            # Config will represent the index of the item to remove
            if config > (len(currentConfig) - 1):
                # Throw Error then return
                print("Out of bounds error")
                return False

            entryID = currentConfig[config][1]
            if type(discordObject) == discord.Guild:
                self._guild_config[discordObject.id]["global"][option].pop(config)
            elif type(discordObject) == discord.TextChannel:
                self._guild_config[discordObject.guild.id]["channels"][discordObject.id][option].pop(config)

            await self.write_config_change(discordObject, option, "remove", config, entryID)
        else:
            # Config should be empty

            pass
        
        return True

    async def getObjectConfig(self, discordObject):
        print(self._guild_config) 
        if type(discordObject) == discord.Guild:
            if discordObject.id not in self._guild_config:
                # Try to get existing config
                await self.load_config_for_guild(discordObject)
                
            # Make sure existing config checked
            if discordObject.id in self._guild_config:
                return self._guild_config[discordObject.id]["global"]

                                            
        elif type(discordObject) == discord.TextChannel:
            if discordObject.guild.id not in self._guild_config:
                await self.load_config_for_guild(discordObject.guild)
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
            
        if "author" in msg_ctx:
            instructions += f"The current message was sent by User {msg_ctx['author'].id} (username: {msg_ctx['author'].name}). "
            if msg_ctx["author"].global_name:
                instructions += f"The User currently has the nickname {msg_ctx['author'].global_name} this guild."

        return instructions


    # Handles actually generating instructions from message
    # Use this instead of genInstructions if you don't need raw control over every argument
    async def genInstructionsFromMessage(self, message: discord.Message, msg_ctx: dict = {}):

        print("Generating Instruction Set")
        #print("previous_messages" in msg_ctx)
        if "previous_messages" not in msg_ctx:
            print("Previous Messages not provided, generating own")
            previous_messages = [msg async for msg in message.channel.history(limit=51)][::-1][:-1]

            msg_ctx["previous_messages"] = list(map(self.formatMessage, previous_messages))

            print("Got previous messages")

        msg_ctx["author"] = message.author
        msg_ctx["datetime"] = message.created_at

        if message.guild:
            msg_ctx["guild"] = message.guild
        
        if message.reference:
            msg_ctx["referenced_msg"] = message.reference

        instructions = await self.genInstructions(msg_ctx)
        
        

        guildInstructions = await self.getObjectConfigOption(message.guild, "instruction")
        channelInstructions = await self.getObjectConfigOption(message.channel, "instruction")

        print(guildInstructions)
        print(channelInstructions)

        if guildInstructions is not None:
            for guildInstruction in guildInstructions:
                instructions += guildInstruction

        if channelInstructions is not None:
            for channelInstruction in channelInstructions:
                instructions += channelInstruction

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

    def semirandomString(self, length=32, charset=string.ascii_letters + string.digits):
        return ''.join(random.choice(charset) for _ in range(length))
        
