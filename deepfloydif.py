import asyncio
import glob
import os
import pathlib
import random

import discord
from gradio_client import Client
from PIL import Image

from discord.ui import Button, View

HF_TOKEN = os.getenv("HF_TOKEN")
deepfloydif_client = Client("huggingface-projects/IF", HF_TOKEN)

BOT_USER_ID = 1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151
DEEPFLOYDIF_CHANNEL_ID = 1121834257959092234 if os.getenv("TEST_ENV", False) else 1119313215675973714


def deepfloydif_generate64_inference(prompt):
    """Generates four images based on a prompt"""
    negative_prompt = ""
    seed = random.randint(0, 1000)
    number_of_images = 4
    guidance_scale = 7
    custom_timesteps_1 = "smart50"
    number_of_inference_steps = 50
    (
        stage_1_images,
        stage_1_param_path,
        path_for_upscale256_upscaling,
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
    return [stage_1_images, stage_1_param_path, path_for_upscale256_upscaling]


def deepfloydif_upscale256_inference(index, path_for_upscale256_upscaling):
    """Upscales one of the images from deepfloydif_generate64_inference based on the chosen index"""
    selected_index_for_upscale256 = index
    seed_2 = 0
    guidance_scale_2 = 4
    custom_timesteps_2 = "smart50"
    number_of_inference_steps_2 = 50
    result_path = deepfloydif_client.predict(
        path_for_upscale256_upscaling,
        selected_index_for_upscale256,
        seed_2,
        guidance_scale_2,
        custom_timesteps_2,
        number_of_inference_steps_2,
        api_name="/upscale256",
    )
    return result_path


def deepfloydif_upscale1024_inference(index, path_for_upscale256_upscaling, prompt):
    """Upscales to stage 2, then stage 3"""
    selected_index_for_upscale256 = index
    seed_2 = 0  # default seed for stage 2 256 upscaling
    guidance_scale_2 = 4  # default for stage 2
    custom_timesteps_2 = "smart50"  # default for stage 2
    number_of_inference_steps_2 = 50  # default for stage 2
    negative_prompt = ""  # empty (not used, could add in the future)

    seed_3 = 0  # default for stage 3 1024 upscaling
    guidance_scale_3 = 9  # default for stage 3
    number_of_inference_steps_3 = 40  # default for stage 3

    result_path = deepfloydif_client.predict(
        path_for_upscale256_upscaling,
        selected_index_for_upscale256,
        seed_2,
        guidance_scale_2,
        custom_timesteps_2,
        number_of_inference_steps_2,
        prompt,
        negative_prompt,
        seed_3,
        guidance_scale_3,
        number_of_inference_steps_3,
        api_name="/upscale1024",
    )
    return result_path


def load_image(png_files, stage_1_images):
    """Opens images as variables so we can combine them later"""
    results = []
    for file in png_files:
        png_path = os.path.join(stage_1_images, file)
        results.append(Image.open(png_path))
    return results


def combine_images(png_files, stage_1_images, partial_path):
    if os.environ.get("TEST_ENV") == "True":
        print("Combining images for deepfloydif_generate64")
    images = load_image(png_files, stage_1_images)
    combined_image = Image.new("RGB", (images[0].width * 2, images[0].height * 2))
    combined_image.paste(images[0], (0, 0))
    combined_image.paste(images[1], (images[0].width, 0))
    combined_image.paste(images[2], (0, images[0].height))
    combined_image.paste(images[3], (images[0].width, images[0].height))
    combined_image_path = os.path.join(stage_1_images, f"{partial_path}.png")
    combined_image.save(combined_image_path)
    return combined_image_path


async def deepfloydif_generate64(ctx, prompt, client):
    """DeepfloydIF command (generate images with realistic text using slash commands)"""
    try:
        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == DEEPFLOYDIF_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safety checks passed for deepfloydif_generate64")
                channel = client.get_channel(DEEPFLOYDIF_CHANNEL_ID)
                # interaction.response message can't be used to create a thread, so we create another message
                message = await ctx.send(f"**{prompt}** - {ctx.author.mention} <a:loading:1114111677990981692>")

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, deepfloydif_generate64_inference, prompt)
                stage_1_images = result[0]
                path_for_upscale256_upscaling = result[2]

                partial_path = pathlib.Path(path_for_upscale256_upscaling).name
                png_files = list(glob.glob(f"{stage_1_images}/**/*.png"))

                if png_files:
                    await message.delete()
                    combined_image_path = combine_images(png_files, stage_1_images, partial_path)
                    if os.environ.get("TEST_ENV") == "True":
                        print("Images combined for deepfloydif_generate64")

                    with Image.open(combined_image_path) as img:
                        width, height = img.size
                        new_width = width * 3
                        new_height = height * 3
                        resized_img = img.resize((new_width, new_height))
                        x2_combined_image_path = combined_image_path
                        resized_img.save(x2_combined_image_path)

                    # making image bigger, more readable
                    with open(x2_combined_image_path, "rb") as f:  # was combined_image_path
                        button1 = Button(custom_id="0", emoji="↖")
                        button2 = Button(custom_id="1", emoji="↗")
                        button3 = Button(custom_id="2", emoji="↙")
                        button4 = Button(custom_id="3", emoji="↘")

                        async def button_callback(interaction):
                            index = int(interaction.data["custom_id"])  # 0,1,2,3

                            await interaction.response.send_message(
                                f"{interaction.user.mention} <a:loading:1114111677990981692>", ephemeral=True
                            )
                            result_path = await deepfloydif_upscale256(index, path_for_upscale256_upscaling)

                            # create and use upscale 1024 button
                            with open(result_path, "rb") as f:
                                upscale1024 = Button(
                                    label="High-quality upscale (x4)", custom_id=str(index)
                                )  # "0", "1" etc
                                upscale1024.callback = upscale1024_callback
                                view = View(timeout=None)
                                view.add_item(upscale1024)

                                await interaction.delete_original_response()
                                await channel.send(
                                    content=(
                                        f"{interaction.user.mention} Here is the upscaled image! Click to upscale even"
                                        " more!"
                                    ),
                                    file=discord.File(f, f"{prompt}.png"),
                                    view=view,
                                )

                        async def upscale1024_callback(interaction):
                            index = int(interaction.data["custom_id"])

                            await interaction.response.send_message(
                                f"{interaction.user.mention} <a:loading:1114111677990981692>", ephemeral=True
                            )
                            result_path = await deepfloydif_upscale1024(index, path_for_upscale256_upscaling, prompt)

                            with open(result_path, "rb") as f:
                                await interaction.delete_original_response()
                                await channel.send(
                                    content=f"{interaction.user.mention} Here's your high-quality x16 image!",
                                    file=discord.File(f, f"{prompt}.png"),
                                )

                        button1.callback = button_callback
                        button2.callback = button_callback
                        button3.callback = button_callback
                        button4.callback = button_callback

                        view = View(timeout=None)
                        view.add_item(button1)
                        view.add_item(button2)
                        view.add_item(button3)
                        view.add_item(button4)

                        # could store this message as combined_image_dfif in case it's useful for future testing
                        await channel.send(
                            f"{ctx.author.mention} Click a button to upscale! (make larger + enhance quality)",
                            file=discord.File(f, f"{partial_path}.png"),
                            view=view,
                        )
                else:
                    await ctx.send(f"{ctx.author.mention} No PNG files were found, cannot post them!")

    except Exception as e:
        print(f"Error: {e}")


async def deepfloydif_upscale256(index: int, path_for_upscale256_upscaling):
    """upscaling function for images generated using /deepfloydif"""
    try:
        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(
            None, deepfloydif_upscale256_inference, index, path_for_upscale256_upscaling
        )
        return result_path

    except Exception as e:
        print(f"Error: {e}")


async def deepfloydif_upscale1024(index: int, path_for_upscale256_upscaling, prompt):
    """upscaling function for images generated using /deepfloydif"""
    try:
        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(
            None, deepfloydif_upscale1024_inference, index, path_for_upscale256_upscaling, prompt
        )
        return result_path

    except Exception as e:
        print(f"Error: {e}")
