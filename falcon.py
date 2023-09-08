import asyncio
import os
from typing import Optional

import gradio_client as grc
from gradio_client.utils import QueueError


HF_TOKEN = os.getenv("HF_TOKEN")


BOT_USER_ID = 1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151
FALCON_CHANNEL_ID = 1079459939405279232 if os.getenv("TEST_ENV", False) else 1119313248056004729


thread_to_client = {}
thread_to_user = {}


async def wait(job):
    while not job.done():
        await asyncio.sleep(0.2)


def get_client(session: Optional[str] = None) -> grc.Client:
    client = grc.Client("huggingface-projects/falcon-180b-discord", hf_token=os.getenv("HF_TOKEN"))
    if session:
        client.session_hash = session
    return client


async def falcon_chat(ctx, prompt):
    """Generates text based on a given prompt"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == FALCON_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safetychecks passed for try_falcon")
                message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
                if len(prompt) > 99:
                    small_prompt = prompt[:99]
                else:
                    small_prompt = prompt
                thread = await message.create_thread(name=small_prompt, auto_archive_duration=60)  # interaction.user

                if os.environ.get("TEST_ENV") == "True":
                    print("Running falcon_initial_generation...")
                loop = asyncio.get_running_loop()
                client = await loop.run_in_executor(None, get_client, None)
                job = client.submit(prompt, api_name="/chat")
                await wait(job)
                try:
                    job.result()
                    response = job.outputs()[-1]
                    await thread.send(response)
                    thread_to_client[thread.id] = client
                    thread_to_user[thread.id] = ctx.author.id
                except QueueError:
                    await thread.send("The gradio space powering this bot is really busy! Please try again later!")
    except Exception as e:
        print(f"chat (180B) Error: {e}")


async def continue_chat(message):
    """Continues a given conversation based on chathistory"""
    try:
        if message.channel.id in thread_to_user:
            if thread_to_user[message.channel.id] == message.author.id:
                client = thread_to_client[message.channel.id]
                job = client.submit(message.content, api_name="/chat")
                await wait(job)
                try:
                    job.result()
                    response = job.outputs()[-1]
                    await message.reply(response)
                except QueueError:
                    await message.reply("The gradio space powering this bot is really busy! Please try again later!")
    except Exception as e:
        print(f"continue_falcon Error: {e}")
        await message.reply(f"Error: {e} <@811235357663297546> (continue_falcon error)")
