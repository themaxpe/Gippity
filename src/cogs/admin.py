import discord
from discord.ext import commands
from discord import app_commands


# Admin cog handles all commands relevant to guild admins
# Cog relies on some gippity-specific functions. Will not be a drop in replacement for cogs in other bots.


class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="instruction", description="Manage custom instructions")
    @app_commands.describe(
            scope="Guild-wide or channel-specific instruction",
            option="Add, view or remove instructions",
            instruction="The new instruction, or the instruction to remove",
    )
    async def manage_instruction(self, interaction: discord.Interaction, scope: str, option: str, instruction: str = ""):

        if option.lower() not in ["add", "view", "remove"]:
            return
   
        obj = None
        if scope == "guild":
            obj = interaction.guild
        elif scope == "channel":
            obj = interaction.channel


        if option == "add":

            if len(instruction) < 0:
                await interaction.response.send_message("No instruction provided!")
                return
            

            await self.bot.addConfigToObject(obj, "instruction", instruction)
        
            await interaction.response.send_message(f"Successfully added instruction to {obj.name}") 
        
        elif option == "view":
            
            config = await self.bot.getObjectConfigOption(obj, "instruction")
            
            embed = discord.Embed(
            title="Instructions",
            description=f"Current Instructions in {obj.name}"
            )
            
            if config is None:
                embed.add_field(name="Empty Config", value=f"No custom instructions in {obj.name}, try using /instruction")
                config = [] # Pass empty config option to for loop :)

            if len(config) > 0:
                instructions = []
                for x in range(len(config)):
                    instructions.append(f"{x+1} ) {config[x][0]}")
    
                embed.add_field(name="Instructions", value='\n'.join(instructions))
                #embed.add_field(name="Instructions", value='\n'.join(map(lambda x: x[0], config)))

            await interaction.response.send_message(embed=embed)


        elif option == "remove":
            print("Someone wants to remove instructions")
            # Instruction will hold the number of the instruction to remove
            await self.bot.removeConfigFromObject(obj, "instruction", instruction) 


        else:
            print("Uh oh")

    @app_commands.command(name="configure", description="Change bot settings")
    @app_commands.describe(
        scope="Guild-wide (guild) or channel-wide (channel)",
        option="Configuration key to change",
        value="New value for the key"
    )
    async def configure_settings(self, interaction: discord.Interaction, scope: str, option: str, value: str):
        pass


        
