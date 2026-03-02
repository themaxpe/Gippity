import warnings
#from cogs import admin
import discord
from gippity import Gippity
import asyncio
import os
from dotenv import load_dotenv
from interface import Responder

from cogs.admin import Admin

load_dotenv()

# Discord config
bot_token = os.getenv("bot_token")
admin_user = int(os.getenv("admin_user")) or 0
if admin_user == 0:
    warnings.warn("No admin user (admin_user) ID provided. Admin commands will NOT function!")

# Base model config
ai_key = os.getenv("ai_key") or "EMPTY"
base_url = os.getenv("base_url") or ""
default_model = os.getenv("default_model") or "" # Get the default model

# Discord Intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

# Set up bot
client = Gippity(command_prefix="g!", intents=intents)

# TODO: Create AI model for each provided set of keys/urls
# Grab AI interface
responder = Responder(ai_key, default_model, base_url)



@client.event
async def on_ready():
    if not os.path.exists("flag"):
        print("Flag does not exist. Running first-time setup")
        with open("flag", "w+") as file:
            file.close()
        await client.tree.sync()

    print("Bot Ready")

@client.tree.command(name="sync", description="Owner only command")
async def sync(interaction: discord.Interaction):
    print(f"{interaction.user} ({interaction.user.id}) requested a sync")
    if interaction.user.id == admin_user:
        print("Requested tree sync")
        await client.tree.sync()

        print("Tree has synced")

# Brunt of work done is handled through simply processing a message
# In future, may add slash commands to extend functionality
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if client.user not in message.mentions:
        if message.reference: # Sometimes references don't mention original user (for some reason) -> Always check!
            referenceAuthor = await client.getMessageFromReference(message.reference)
            referenceAuthor = referenceAuthor.author
            if referenceAuthor != client.user.id:
                return
        else:
            return
    
    if message.reference:
        print(message.reference)

    images = []
    _imageTypes = ("image/png", "image/jpeg", "image/jpg", "image/webp")
    for attachment in (message.attachments or []):
        if attachment.content_type in _imageTypes:
            images.append(attachment.url)

    instructions = await client.genInstructionsFromMessage(message, msg_ctx={})
    print("Instructions Generated")
    response = responder.generate_response(message.content, instructions, images) 

    # Send response to discord
    for chunk in range(len(response) % 2000):
        await message.channel.send(response[(2000 * chunk) : (2000 * (chunk + 1))])
        await asyncio.sleep(1) 

async def main():

    async with client:
        # Load Cogs
        await client.add_cog(Admin(client))
        
        # Run Bot
        await client.start(bot_token)

asyncio.run(main())
