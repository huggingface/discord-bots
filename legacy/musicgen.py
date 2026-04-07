import asyncio
import os
import threading
import random
from threading import Event
from typing import Optional

import discord
import gradio as gr
from discord.ext import commands

import gradio_client as grc
from gradio_client.utils import QueueError

event = Event()

# HF GUILD SETTINGS
# taken from here https://huggingface.co/spaces/huggingface-projects/huggingbots/blob/main/app.py
MY_GUILD_ID = 1077674588122648679 if os.getenv("TEST_ENV", False) else 879548962464493619
MY_GUILD = discord.Object(id=MY_GUILD_ID)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)


async def wait(job):
    while not job.done():
        await asyncio.sleep(0.2)


def get_client(session: Optional[str] = None) -> grc.Client:
    client = grc.Client("huggingface-projects/transformers-musicgen", hf_token=os.getenv("HF_TOKEN"))
    if session:
        client.session_hash = session
    return client


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

async def setup_hook():
    await bot.wait_until_ready()
    synced = await bot.tree.sync(guild=discord.Object(MY_GUILD_ID))
    print(f"Synced commands: {', '.join([s.name for s in synced])}.")
    print("------")


@bot.hybrid_command(
    name="musicgen",
    description="Enter a prompt to generate music!",
)
async def musicgen_command(ctx, prompt: str, seed: int = None):
    """Generates music based on a prompt"""
    if ctx.author.id == bot.user.id:
        return
    if seed is None:
        seed = random.randint(1, 10000)
    try:
        await music_create(ctx, prompt, seed)
    except Exception as e:
        print(f"Error: {e}")


async def music_create(ctx, prompt, seed):
    """Runs music_create_job in executor"""
    try:
        message = await ctx.send(f"**{prompt}** - {ctx.author.mention} Generating...")
        thread = await message.create_thread(name=prompt[:100])

        loop = asyncio.get_running_loop()
        client = await loop.run_in_executor(None, get_client, None)
        job = client.submit(prompt, seed, api_name="/predict")
        await wait(job)

        try:
            job.result()
            files = job.outputs()
            media_files = files[0]
            audio = media_files[0]
            video = media_files[1]
            short_filename = prompt[:20]
            audio_filename = f"{short_filename}.mp3"
            video_filename = f"{short_filename}.mp4"

            with open(video, "rb") as file:
                discord_video_file = discord.File(file, filename=video_filename)
            await thread.send(file=discord_video_file)

            with open(audio, "rb") as file:
                discord_audio_file = discord.File(file, filename=audio_filename)
            await thread.send(file=discord_audio_file)

        except QueueError:
            await ctx.send("The gradio space powering this bot is really busy! Please try again later!")

    except Exception as e:
        print(f"music_create Error: {e}")


def run_bot():
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN NOT SET")
        event.set()
    else:
        bot.run(DISCORD_TOKEN)


threading.Thread(target=run_bot).start()

event.wait()

welcome_message = """
## Add this bot to your server by clicking this link: 

https://discord.com/api/oauth2/authorize?client_id=1150383223021506620&permissions=326417565696&scope=bot

## How to use it?

The bot can be triggered via `/musicgen` followed by your text prompt.

This will generate music based on your text prompt!

⚠️ Note ⚠️: Please make sure this bot's command does have the same name as another command in your server.

⚠️ Note ⚠️: Bot commands do not work in DMs with the bot as of now.
"""


with gr.Blocks() as demo:
    gr.Markdown(f"""
    # Discord bot of https://huggingface.co/spaces/facebook/MusicGen
    {welcome_message}
    """)

demo.launch()
