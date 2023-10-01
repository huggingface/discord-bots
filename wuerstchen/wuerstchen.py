import asyncio
import glob
import os
import random
import threading
from discord.ext import commands
import discord
import gradio as gr
from gradio_client import Client


HF_TOKEN = os.getenv("HF_TOKEN")
wuerstchen_client = Client("huggingface-projects/Wuerstchen-duplicate", HF_TOKEN)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    synced = await bot.tree.sync()
    print(f"Synced commands: {', '.join([s.name for s in synced])}.")
    print("------")


@bot.hybrid_command(
    name="wuerstchen",
    description="Enter a prompt to generate art!",
)
async def wuerstchen_command(ctx, prompt: str):
    """Wuerstchen generation"""
    try:
        await run_wuerstchen(ctx, prompt)
    except Exception as e:
        print(f"Error wuerstchen: (app.py){e}")


def wuerstchen_inference(prompt):
    """Inference for Wuerstchen"""
    negative_prompt = ""
    seed = random.randint(0, 1000)
    width = 1024
    height = 1024
    prior_num_inference_steps = 60
    prior_guidance_scale = 4
    decoder_num_inference_steps = 12
    decoder_guidance_scale = 0
    num_images_per_prompt = 1

    result_path = wuerstchen_client.predict(
        prompt,
        negative_prompt,
        seed,
        width,
        height,
        prior_num_inference_steps,
        prior_guidance_scale,
        decoder_num_inference_steps,
        decoder_guidance_scale,
        num_images_per_prompt,
        api_name="/run",
    )
    png_file = list(glob.glob(f"{result_path}/**/*.png"))
    return png_file[0]


async def run_wuerstchen(ctx, prompt):
    """Responds to /Wuerstchen command"""
    try:
        message = await ctx.send(f"**{prompt}** - {ctx.author.mention} (generating...)")

        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(None, wuerstchen_inference, prompt)

        await message.delete()
        with open(result_path, "rb") as f:
            await ctx.channel.send(f"**{prompt}** - {ctx.author.mention}", file=discord.File(f, "wuerstchen.png"))
    except Exception as e:
        print(f"Error: {e}")


def run_bot():
    bot.run(DISCORD_TOKEN)


threading.Thread(target=run_bot).start()
"""This allows us to run the Discord bot in a Python thread"""


welcome_message = """
## Add this bot to your server by clicking this link: 

https://discord.com/api/oauth2/authorize?client_id=1155489509518098565&permissions=51200&scope=bot

## How to use it?

The bot can be triggered via `/wuerstchen` followed by your text prompt.

This will generate an image based on your prompt, which is then posted in the channel!

⚠️ Note ⚠️: Please make sure this bot's command does have the same name as another command in your server.

⚠️ Note ⚠️: Bot commands do not work in DMs with the bot as of now.
"""


with gr.Blocks() as demo:
    gr.Markdown(f"""
    # Discord bot of https://huggingface.co/spaces/warp-ai/Wuerstchen
    {welcome_message}
    """)


demo.queue(concurrency_count=100)
demo.queue(max_size=100)
demo.launch()
