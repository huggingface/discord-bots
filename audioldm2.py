import asyncio
import os
import random
from datetime import datetime

import discord
from gradio_client import Client
from gradio_client.utils import QueueError

BOT_USER_ID = 1102236653545861151  # real
MUSIC_CHANNEL_ID = 1143183148881035365  # real


HF_TOKEN = os.getenv("HF_TOKEN")
audioldm2 = Client("huggingface-projects/audioldm2-text2audio-text2music", HF_TOKEN)


def audioldm2_create_job(prompt):
    """Generates a sound or music based on a given prompt"""
    try:
        random.seed(datetime.now().timestamp())
        guidance_scale = 6  # between 1-6, larger = better, smaller = diverser
        seed = random.randint(1, 1000)
        quality_control = 3  # between 1-3, higher = longer compute but better results
        job = audioldm2.submit(prompt, guidance_scale, seed, quality_control, fn_index=0)
        while not job.done():
            pass
        return job

    except Exception as e:
        print(f"audioldm2_create_job Error: {e}")


async def audioldm2_create(ctx, prompt):
    """Runs audioldm2_create_job in executor"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == MUSIC_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safetychecks passed for audioldm2_create")

                message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
                if len(prompt) > 99:
                    small_prompt = prompt[:99]
                else:
                    small_prompt = prompt
                thread = await message.create_thread(name=small_prompt, auto_archive_duration=60)

                await thread.send(
                    "[DISCLAIMER: HuggingBot is a beta feature; The AudioLDM2"
                    " model can be found here: https://huggingface.co/spaces/"
                    "haoheliu/audioldm2-text2audio-text2music]"
                )
                if os.environ.get("TEST_ENV") == "True":
                    print("Running audioldm2_create_job...")

                loop = asyncio.get_running_loop()
                job = await loop.run_in_executor(None, audioldm2_create_job, prompt)

                try:
                    job.result()
                    video = job.outputs()[0]
                except QueueError:
                    await thread.send("The gradio space powering this bot is really busy! Please try again later!")

                with open(video, "rb") as file:
                    discord_file = discord.File(file)
                await thread.send(file=discord_file)

    except Exception as e:
        print(f"audioldm2_create Error: {e}")
