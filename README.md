# Gippity
A simple Discord bot that connects to an AI interface.

# Features
- Simple integration with many AI models and platforms  
- Per-server and per-channel configuration  
- Respond to many forms of Discord messages  
- Per-channel memory  

# Setting up the bot
The bot requires certain environment variables to be set.  
These can be done either within the environment (useful for Heroku and other hosts).  
Alternatively, create a .env file in the directory from which you run the program.  

The following environment variables are usable:  
bot_token - The Discord bot token (Required, obviously)  
ai_key - The AI Api Key (Optional)  
base_url - The URL of the AI API (Optional - required if an OpenAI API Key is not provided)  

# Using the bot
Running the bot is as simple as executing the main.py file.  
By default, users can mention the bot in a message and it'll respond to that message within the context of the channel.

# TODO
--1. Allow the bot to respond to replies--
2. More configuration (personality traits, custom instructions, etc...)
3. Support for multiple models at once


