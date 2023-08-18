import os
import threading

import discord
import gradio as gr
from deepfloydif import deepfloydif_stage_1, deepfloydif_stage_2_react_check
from discord import app_commands
from discord.ext import commands
from falcon import continue_falcon, try_falcon
from musicgen import music_create


# HF GUILD SETTINGS
MY_GUILD_ID = 1077674588122648679 if os.getenv("TEST_ENV", False) else 879548962464493619
MY_GUILD = discord.Object(id=MY_GUILD_ID)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)


class Bot(commands.Bot):
    """This structure allows slash commands to work instantly."""

    def __init__(self):
        super().__init__(command_prefix="/", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(MY_GUILD_ID))
        print(f"Synced slash commands for {self.user}.")


client = Bot()


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("------")


@client.hybrid_command(
    name="falcon",
    with_app_command=True,
    description="Enter some text to chat with the bot! Like this: /falcon Hello, how are you?",
)
@app_commands.guilds(MY_GUILD)
async def falcon(ctx, prompt: str):
    """Command that begins a new conversation with Falcon"""
    try:
        await try_falcon(ctx, prompt)
    except Exception as e:
        print(f"Error: {e}")


@client.event
async def on_message(message):
    """Checks channel and continues Falcon conversation if it's the right Discord Thread"""
    try:
        await continue_falcon(message)
    except Exception as e:
        print(f"Error: {e}")


@client.hybrid_command(
    name="deepfloydif",
    with_app_command=True,
    description="Enter a prompt to generate an image! Can generate realistic text, too!",
)
@app_commands.guilds(MY_GUILD)
async def deepfloydif(ctx, prompt: str):
    """DeepfloydIF stage 1 generation"""
    try:
        await deepfloydif_stage_1(ctx, prompt, client)
    except Exception as e:
        print(f"Error: {e}")


@client.hybrid_command(name="musicgen", with_app_command=True, description="Enter a prompt to generate music!")
@app_commands.guilds(MY_GUILD)
async def musicgen(ctx, prompt: str):
    """Generates music based on a prompt"""
    try:
        await music_create(ctx, prompt)
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
demo.queue(concurrency_count=100)
demo.queue(max_size=100)
demo.launch()
