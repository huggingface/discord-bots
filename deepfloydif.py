import asyncio
import glob
import os
import pathlib
import random

import discord
from gradio_client import Client
from PIL import Image

HF_TOKEN = os.getenv("HF_TOKEN")
deepfloydif_client = Client("huggingface-projects/IF", HF_TOKEN)

BOT_USER_ID = 1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151
DEEPFLOYDIF_CHANNEL_ID = 1121834257959092234 if os.getenv("TEST_ENV", False) else 1119313215675973714


def deepfloydif_stage_1_inference(prompt):
    """Generates an image based on a prompt"""
    negative_prompt = ""
    seed = random.randint(0, 1000)
    number_of_images = 4
    guidance_scale = 7
    custom_timesteps_1 = "smart50"
    number_of_inference_steps = 50
    (
        stage_1_images,
        stage_1_param_path,
        path_for_stage_2_upscaling,
    ) = deepfloydif_client.predict(
        prompt,
        negative_prompt,
        seed,
        number_of_images,
        guidance_scale,
        custom_timesteps_1,
        number_of_inference_steps,
        api_name="/generate64",
    )
    return [stage_1_images, stage_1_param_path, path_for_stage_2_upscaling]


def deepfloydif_stage_2_inference(index, path_for_stage_2_upscaling):
    """Upscales one of the images from deepfloydif_stage_1_inference based on the chosen index"""
    selected_index_for_stage_2 = index
    seed_2 = 0
    guidance_scale_2 = 4
    custom_timesteps_2 = "smart50"
    number_of_inference_steps_2 = 50
    result_path = deepfloydif_client.predict(
        path_for_stage_2_upscaling,
        selected_index_for_stage_2,
        seed_2,
        guidance_scale_2,
        custom_timesteps_2,
        number_of_inference_steps_2,
        api_name="/upscale256",
    )
    return result_path


async def react_1234(reaction_emojis, combined_image_dfif):
    """Sets up 4 reaction emojis so the user can choose an image to upscale for deepfloydif"""
    for emoji in reaction_emojis:
        await combined_image_dfif.add_reaction(emoji)


def load_image(png_files, stage_1_images):
    """Opens images as variables so we can combine them later"""
    results = []
    for file in png_files:
        png_path = os.path.join(stage_1_images, file)
        results.append(Image.open(png_path))
    return results


def combine_images(png_files, stage_1_images, partial_path):
    if os.environ.get("TEST_ENV") == "True":
        print("Combining images for deepfloydif_stage_1")
    images = load_image(png_files, stage_1_images)
    combined_image = Image.new("RGB", (images[0].width * 2, images[0].height * 2))
    combined_image.paste(images[0], (0, 0))
    combined_image.paste(images[1], (images[0].width, 0))
    combined_image.paste(images[2], (0, images[0].height))
    combined_image.paste(images[3], (images[0].width, images[0].height))
    combined_image_path = os.path.join(stage_1_images, f"{partial_path}.png")
    combined_image.save(combined_image_path)
    return combined_image_path


async def deepfloydif_stage_1(ctx, prompt, client):
    """DeepfloydIF command (generate images with realistic text using slash commands)"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == DEEPFLOYDIF_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safety checks passed for deepfloydif_stage_1")
                # interaction.response message can't be used to create a thread, so we create another message
                message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
                if len(prompt) > 99:
                    small_prompt = prompt[:99]
                else:
                    small_prompt = prompt                    
                thread = await message.create_thread(name=f"{small_prompt}", auto_archive_duration=60)
                await thread.send(
                    "[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; Additional information on the"
                    " DeepfloydIF model can be found here: https://huggingface.co/spaces/DeepFloyd/IF"
                )
                await thread.send(f"{ctx.author.mention} Generating images in thread, can take ~1 minute...")

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, deepfloydif_stage_1_inference, prompt)
                stage_1_images = result[0]
                path_for_stage_2_upscaling = result[2]

                partial_path = pathlib.Path(path_for_stage_2_upscaling).name
                png_files = list(glob.glob(f"{stage_1_images}/**/*.png"))

                if png_files:
                    combined_image_path = combine_images(png_files, stage_1_images, partial_path)
                    if os.environ.get("TEST_ENV") == "True":
                        print("Images combined for deepfloydif_stage_1")
                    with open(combined_image_path, "rb") as f:
                        combined_image_dfif = await thread.send(
                            f"{ctx.author.mention} React with the image number you want to upscale!",
                            file=discord.File(f, f"{partial_path}.png"),
                        )
                    emoji_list = ["↖️", "↗️", "↙️", "↘️"]
                    await react_1234(emoji_list, combined_image_dfif)
                else:
                    await thread.send(f"{ctx.author.mention} No PNG files were found, cannot post them!")

    except Exception as e:
        print(f"Error: {e}")


async def deepfloydif_stage_2_react_check(reaction, user):
    """Checks for a reaction in order to call dfif2"""
    try:
        if os.environ.get("TEST_ENV") == "True":
            print("Running deepfloydif_stage_2_react_check")
        global BOT_USER_ID
        global DEEPFLOYDIF_CHANNEL_ID
        if user.id != BOT_USER_ID:
            thread = reaction.message.channel
            thread_parent_id = thread.parent.id
            if thread_parent_id == DEEPFLOYDIF_CHANNEL_ID:
                if reaction.message.attachments:
                    if user.id == reaction.message.mentions[0].id:
                        attachment = reaction.message.attachments[0]
                        image_name = attachment.filename
                        partial_path = image_name[:-4]
                        full_path = "/tmp/" + partial_path
                        emoji = reaction.emoji
                        if emoji == "↖️":
                            index = 0
                        elif emoji == "↗️":
                            index = 1
                        elif emoji == "↙️":
                            index = 2
                        elif emoji == "↘️":
                            index = 3
                        path_for_stage_2_upscaling = full_path
                        thread = reaction.message.channel
                        await deepfloydif_stage_2(
                            index,
                            path_for_stage_2_upscaling,
                            thread,
                        )
    except Exception as e:
        print(f"Error: {e} (known error, does not cause issues, low priority)")


async def deepfloydif_stage_2(index: int, path_for_stage_2_upscaling, thread):
    """upscaling function for images generated using /deepfloydif"""
    try:
        if os.environ.get("TEST_ENV") == "True":
            print("Running deepfloydif_stage_2")
        if index == 0:
            position = "top left"
        elif index == 1:
            position = "top right"
        elif index == 2:
            position = "bottom left"
        elif index == 3:
            position = "bottom right"
        await thread.send(f"Upscaling the {position} image...")

        # run blocking function in executor
        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(
            None, deepfloydif_stage_2_inference, index, path_for_stage_2_upscaling
        )

        with open(result_path, "rb") as f:
            await thread.send("Here is the upscaled image!", file=discord.File(f, "result.png"))
        await thread.edit(archived=True)
    except Exception as e:
        print(f"Error: {e}")
