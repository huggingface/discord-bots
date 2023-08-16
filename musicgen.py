import asyncio
import os

import discord
from gradio_client import Client

BOT_USER_ID = 1102236653545861151  # real
MUSIC_CHANNEL_ID = 1140990231730987058  # real

musicgen = Client("huggingface-projects/transformers-musicgen", hf_token=os.getenv("HF_TOKEN"))


def music_create_job(prompt):
    """Generates music based on a given prompt"""
    try:
        job = musicgen.submit(prompt, api_name="/predict")
        while not job.done():
            pass
        files = job.outputs()
        files = files[0]

        return files

    except Exception as e:
        print(f"music_create_job Error: {e}")


async def music_create(ctx, prompt):
    """Runs music_create_job in executor"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == MUSIC_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safetychecks passed for music_create")

                message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
                thread = await message.create_thread(name=prompt, auto_archive_duration=60)

                await thread.send(
                    "[DISCLAIMER: HuggingBot is a beta feature; The MusicGen"
                    " model can be found here: https://huggingface.co/spaces/facebook/MusicGen]"
                )
                if os.environ.get("TEST_ENV") == "True":
                    print("Running music_create_job...")

                loop = asyncio.get_running_loop()
                output_files = await loop.run_in_executor(None, music_create_job, prompt)

                audio, video = files[0], files[1]

                with open(audio, "rb") as file:
                    discord_file = discord.File(file)
                await thread.send(file=discord_file)

                with open(video, "rb") as file:
                    discord_file = discord.File(file)
                await thread.send(file=discord_file)

                embed = discord.Embed()
                embed.set_thumbnail(url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
                tweet1 = "https://twitter.com/intent/tweet?text="
                tweet2 = "I%20generated%20this%20audio%20using%20MusicGen"
                tweet3 = "%20in%20the%20%F0%9F%A4%97%20@huggingface%20Discord!"
                tweet4 = "%0Ahf.co/join/discord%0APrompt:%20"
                prompt = prompt.replace(" ", "%20")
                intent_link = f"{tweet1}{tweet2}{tweet3}{tweet4}{prompt}"
                embed.add_field(
                    name="Twitter",
                    value=f"[Share it!]({intent_link})",
                    inline=True,
                )

                await thread.send(embed=embed)

    except Exception as e:
        print(f"music_create Error: {e}")
