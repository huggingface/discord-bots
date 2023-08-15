import os
import discord
from gradio_client import Client
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio

MUSIC_CHANNEL_ID = 1140990231730987058  # real musicgen channel

musicgen = Client("huggingface-projects/transformers-musicgen", hf_token=os.getenv("HF_TOKEN"))


async def music_create(ctx, prompt):
    """Generates music based on a given prompt"""
    try:
        if ctx.channel.id == MUSIC_CHANNEL_ID:
            message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
            thread = await message.create_thread(name=prompt, auto_archive_duration=60)
            # clean this v
            await thread.send(
                "[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; The MusicGen"
                " model can be found here: https://huggingface.co/spaces/facebook/MusicGen]"
            )
            job = musicgen.submit(prompt, api_name="/predict")
            while not job.done():
                pass
            input_file = job.outputs()[0]
            output_file = f"/tmp/gradio/{ctx.author.id}.mp3"
            ffmpeg_extract_audio(input_file, output_file)

            with open(output_file, "rb") as file:
                discord_file = discord.File(file)
            await thread.send(file=discord_file)

    except Exception as e:
        print(f"musicgen Error: {e}")
