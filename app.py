import discord
from discord import app_commands
import gradio as gr
import os
import threading
from falcon import try_falcon
from falcon import continue_falcon
from deepfloydif import deepfloydif_stage_1
from deepfloydif import deepfloydif_stage_2_react_check

# HF GUILD SETTINGS
MY_GUILD_ID = 1077674588122648679 if os.getenv("TEST_ENV", False) else 879548962464493619
MY_GUILD = discord.Object(id=MY_GUILD_ID)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)


class MyClient(discord.Client):
    """This structure allows slash commands to work instantly."""

    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to our guild
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


client = MyClient(intents=discord.Intents.all())


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("------")


@client.tree.command()
@app_commands.describe(prompt="Enter some text to chat with the bot! Like this: /falcon Hello, how are you?")
async def falcon(interaction: discord.Interaction, prompt: str):
    """Command that begins a new conversation with Falcon"""
    try:
        await try_falcon(interaction, prompt)
    except Exception as e:
        print(f"Error: {e}")


@client.event
async def on_message(message):
    """Checks channel and continues Falcon conversation if it's the right Discord Thread"""
    try:
        await continue_falcon(message)
    except Exception as e:
        print(f"Error: {e}")


@client.tree.command()
@app_commands.describe(prompt="Enter a prompt to generate an image! Can generate realistic text, too!")
async def deepfloydif(interaction: discord.Interaction, prompt: str):
    """DeepfloydIF stage 1 generation"""
    try:
        await deepfloydif_stage_1(interaction, prompt, client)
    except Exception as e:
        print(f"Error: {e}")


@client.event
async def on_reaction_add(reaction, user):
    """Checks for a reaction in order to call dfif2"""
    try:
        await deepfloydif_stage_2_react_check(reaction, user)
    except Exception as e:
        print(f"Error: {e} (known error, does not cause issues, low priority)")


def run_bot():
    client.run(DISCORD_TOKEN)


threading.Thread(target=run_bot).start()
"""This allows us to run the Discord bot in a Python thread"""
with gr.Blocks() as demo:
    gr.Markdown("""
    # Huggingbots Server
    This space hosts the huggingbots discord bot.
    Currently supported models are Falcon and DeepfloydIF
    """)
demo.queue(concurrency_count=20)
demo.launch()
