import asyncio
import glob
import os
import random

import discord
from gradio_client import Client


HF_TOKEN = os.getenv("HF_TOKEN")
wuerstchen_client = Client("huggingface-projects/Wuerstchen-duplicate", HF_TOKEN)

BOT_USER_ID = 1102236653545861151
WUERSTCHEN_CHANNEL_ID = 1151792944676864041


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


async def run_wuerstchen(ctx, prompt, client):
    """Responds to /Wuerstchen command"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == WUERSTCHEN_CHANNEL_ID:
                channel = client.get_channel(WUERSTCHEN_CHANNEL_ID)
                message = await ctx.send(f"**{prompt}** - {ctx.author.mention} <a:loading:1114111677990981692>")

                loop = asyncio.get_running_loop()
                result_path = await loop.run_in_executor(None, wuerstchen_inference, prompt)

                await message.delete()
                with open(result_path, "rb") as f:
                    await channel.send(f"**{prompt}** - {ctx.author.mention}", file=discord.File(f, "wuerstchen.png"))
    except Exception as e:
        print(f"Error: {e}")
