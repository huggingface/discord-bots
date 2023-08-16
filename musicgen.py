import os

import discord
from gradio_client import Client

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
                "[DISCLAIMER: HuggingBot is a beta feature; The MusicGen"
                " model can be found here: https://huggingface.co/spaces/facebook/MusicGen]"
            )
            await thread.send("Please wait for the song to finish generating before generating a new one!")
            job = musicgen.submit(prompt, api_name="/predict")
            while not job.done():
                pass
            files = job.outputs()
            files = files[0]
            audio = files[0]
            video = files[1]
            
            with open(audio, "rb") as file:
                discord_file = discord.File(file)
            await thread.send(file=discord_file)
            
            with open(video, "rb") as file:
                discord_file = discord.File(file)
            await thread.send(file=discord_file)          

            embed = discord.Embed()
            embed.set_thumbnail(url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
            embed.add_field(name="Twitter", value="[Share it!](https://twitter.com/compose/tweet)", inline=True)

            await thread.send(embed=embed)

    except Exception as e:
        print(f"musicgen Error: {e}")
