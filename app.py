from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from discord import Embed, Color
import gradio_client
import gradio as gr
from gradio_client import Client
import os
import threading 
import requests
import json
import random
import time
import re
from PIL import Image
import asyncio
import concurrent.futures
import multiprocessing
import glob

# HF GUILD SETTINGS
MY_GUILD = discord.Object(id=879548962464493619)  # HF = 879548962464493619, test = 1077674588122648679
HF_TOKEN = os.getenv('HF_TOKEN')
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)

falcon_userid_threadid_dictionary = {}
threadid_conversation = {}
GUILD_ID = 879548962464493619 # 1077674588122648679 = test
FALCON_CHANNEL_ID = 1119313248056004729 #  1079459939405279232 = test
DEEPFLOYD_CHANNEL_ID = 1119313215675973714 # 1121834257959092234 = test
BOT_USER_ID = 1102236653545861151 # 1086256910572986469 = test

# TEST GUILD SETTINGS
''' 
MY_GUILD = discord.Object(id=879548962464493619)  # HF = 879548962464493619, test = 1077674588122648679
HF_TOKEN = os.getenv('HF_TOKEN')
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)

falcon_userid_threadid_dictionary = {}
threadid_conversation = {}
GUILD_ID = 1077674588122648679 # 1077674588122648679 = test
FALCON_CHANNEL_ID = 1079459939405279232 #  1079459939405279232 = test
DEEPFLOYD_CHANNEL_ID = 1121834257959092234 # 1121834257959092234 = test
BOT_USER_ID = 1086256910572986469 # 1086256910572986469 = test
'''

# HF =   <a:loading:1114111677990981692>
# test = 🔁

# HF = <:agree:1098629085955113011>
# test = ✔️

# HF = <:disagree:1098628957521313892>
# test = ❌

df = Client("huggingface-projects/IF", HF_TOKEN)
falconclient = Client("HuggingFaceH4/falcon-chat", HF_TOKEN)
instructions = "The following is a conversation between a highly knowledgeable " \
"and intelligent AI assistant, called Falcon, and a human user, called User. In the " \
"following interactions, User and Falcon will converse in natural language, and Falcon " \
"will answer User's questions. Falcon was built to be respectful, polite and inclusive. " \
"Falcon was built by the Technology Innovation Institute in Abu Dhabi. Falcon will never " \
"decline to answer a question, and always attempts to give an answer that User would be satisfied " \
"with. It knows a lot, and always tells the truth. The conversation begins."


#-------------------------------------------------------------------------------------------------------------------------------------
# This structure allows commands to work instantly (instead of needing to sync global commands for up to an hour)
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to our guild
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

intents = discord.Intents.all() 
client = MyClient(intents=intents)
#-------------------------------------------------------------------------------------------------------------------------------------
@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
#-------------------------------------------------------------------------------------------------------------------------------------  
# deepfloydif stage 1 generation
def inference(prompt):
    negative_prompt = ''
    seed = random.randint(0, 1000)
    #seed = 1
    number_of_images = 4
    guidance_scale = 7
    custom_timesteps_1 = 'smart50'
    number_of_inference_steps = 50
    
    stage_1_results, stage_1_param_path, stage_1_result_path = df.predict(
        prompt, negative_prompt, seed, number_of_images, guidance_scale, custom_timesteps_1, number_of_inference_steps, api_name='/generate64')
    
    return [stage_1_results, stage_1_param_path, stage_1_result_path]        
#------------------------------------------------------------------------------------------------------------------------------------- 
# deepfloydif stage 2 upscaling
def inference2(index, stage_1_result_path):
    selected_index_for_stage_2 = index
    seed_2 = 0
    guidance_scale_2 = 4
    custom_timesteps_2 = 'smart50'
    number_of_inference_steps_2 = 50
    result_path = df.predict(stage_1_result_path, selected_index_for_stage_2, seed_2, 
                             guidance_scale_2, custom_timesteps_2, number_of_inference_steps_2, api_name='/upscale256')
    
    return result_path    
#------------------------------------------------------------------------------------------------------------------------------------- 
async def react1234(reaction_emojis, combined_image_dfif):
    for emoji in reaction_emojis:
        await combined_image_dfif.add_reaction(emoji) 
#------------------------------------------------------------------------------------------------------------------------------------- 
# deepfloydIF command (generate images with realistic text using slash commands)
@client.tree.command()
@app_commands.describe(
    prompt='Enter a prompt to generate an image! Can generate realistic text, too!')
async def deepfloydif(interaction: discord.Interaction, prompt: str):
    thread = None
    try:
        global BOT_USER_ID
        global DEEPFLOYD_CHANNEL_ID
        if interaction.user.id != BOT_USER_ID:
            if interaction.channel.id == DEEPFLOYD_CHANNEL_ID:
                await interaction.response.send_message(f"Working on it!")
                channel = interaction.channel
                message = await channel.send(f"DeepfloydIF Thread")
                await message.add_reaction('<a:loading:1114111677990981692>')
                thread = await message.create_thread(name=f'{prompt}', auto_archive_duration=60) 
                await thread.send(f"[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; Additional information" \
                f" on the DeepfloydIF model can be found here: https://huggingface.co/spaces/DeepFloyd/IF")

                dfif_command_message_id = message.id # used for updating the 'status' of our generations using reaction emojis
                
                await thread.send(f'{interaction.user.mention}Generating images in thread, can take ~1 minute...')

                # generation
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, inference, prompt)  
                stage_1_results = result[0]
                stage_1_result_path = result[2]
                partialpath = stage_1_result_path[5:]
                png_files = list(glob.glob(f"{stage_1_results}/**/*.png"))

                if png_files:
                    first_png = png_files[0]
                    second_png = png_files[1]
                    third_png = png_files[2]
                    fourth_png = png_files[3]
                
                    first_png_path = os.path.join(stage_1_results, first_png)
                    second_png_path = os.path.join(stage_1_results, second_png)
                    third_png_path = os.path.join(stage_1_results, third_png)
                    fourth_png_path = os.path.join(stage_1_results, fourth_png)
                
                    img1 = Image.open(first_png_path)
                    img2 = Image.open(second_png_path)
                    img3 = Image.open(third_png_path)
                    img4 = Image.open(fourth_png_path)
                
                    combined_image = Image.new('RGB', (img1.width * 2, img1.height * 2))
                
                    combined_image.paste(img1, (0, 0))
                    combined_image.paste(img2, (img1.width, 0))
                    combined_image.paste(img3, (0, img1.height))
                    combined_image.paste(img4, (img1.width, img1.height))
                
                    combined_image_path = os.path.join(stage_1_results, f'{partialpath}{dfif_command_message_id}.png')
                    combined_image.save(combined_image_path)

                    with open(combined_image_path, 'rb') as f:
                        combined_image_dfif = await thread.send(f'{interaction.user.mention}React with the image number you want to upscale!', file=discord.File(
                            f, f'{partialpath}{dfif_command_message_id}.png')) # named something like: tmpgtv4qjix1111269940599738479.png                

                    emoji_list = ['↖️', '↗️', '↙️', '↘️']
                    await react1234(emoji_list, combined_image_dfif)
                        
                    await message.remove_reaction('<a:loading:1114111677990981692>', client.user)
                    await message.add_reaction('<:agree:1098629085955113011>')

    except Exception as e:
        print(f"Error: {e}")
        await message.remove_reaction('<a:loading:1114111677990981692>', client.user)
        await message.add_reaction('<:disagree:1098628957521313892>')
        #await thread.send(f"Error: {e} <@811235357663297546> (continue_falcon error)")
#-------------------------------------------------------------------------------------------------------------------------------------   
# upscaling function for images generated using /deepfloydif
async def dfif2(index: int, stage_1_result_path, thread, dfif_command_message_id): 
    try:
        #await thread.send(f"inside dfif2")
        parent_channel = thread.parent
        dfif_command_message = await parent_channel.fetch_message(dfif_command_message_id)
        await dfif_command_message.remove_reaction('<:agree:1098629085955113011>', client.user)
        await dfif_command_message.add_reaction('<a:loading:1114111677990981692>')
        #await thread.send(f"getting index")
        number = index + 1
        if number == 1:
            position = "top left"
        elif number == 2:
            position = "top right"
        elif number == 3:
            position = "bottom left"
        elif number == 4:
            position = "bottom right" 
        await thread.send(f"Upscaling the {position} image...")  
        
        # run blocking function in executor
        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(None, inference2, index, stage_1_result_path) 

        #await thread.send(f"✅upscale done")          
        with open(result_path, 'rb') as f:
            await thread.send(f'Here is the upscaled image!', file=discord.File(f, 'result.png'))
            
        await dfif_command_message.remove_reaction('<a:loading:1114111677990981692>', client.user)
        await dfif_command_message.add_reaction('<:agree:1098629085955113011>')
        await thread.edit(archived=True)

    except Exception as e:
        print(f"Error: {e}")
        parent_channel = thread.parent
        dfif_command_message = await parent_channel.fetch_message(dfif_command_message_id)
        await dfif_command_message.remove_reaction('<a:loading:1114111677990981692>', client.user)
        await dfif_command_message.add_reaction('<:disagree:1098628957521313892>')  
        await thread.send(f"Error during stage 2 upscaling, {e}") 
        await fullqueue(e, thread)
        await thread.edit(archived=True)
#-------------------------------------------------------------------------------------------------------------------------------------
@client.event
async def on_reaction_add(reaction, user): 
    try:
        global BOT_USER_ID
        global DEEPFLOYD_CHANNEL_ID
        channel = reaction.message.channel
        #await channel.send("reaction detected")
        if user.id != BOT_USER_ID: # 
            thread = reaction.message.channel
            threadparentid = thread.parent.id
            #await channel.send(f"threadparentid = {threadparentid}")
            if threadparentid == DEEPFLOYD_CHANNEL_ID: # 1121834257959092234
                #await channel.send(f"right parent")
                if reaction.message.attachments:
                    #await channel.send(f"has attachments")
                    if user.id == reaction.message.mentions[0].id:  #  if user.id == reaction.message.mentions[0].id:  
                        #await channel.send("checks passed for on_react")
                        #await reaction.message.channel.send("✅reaction detected")
                        attachment = reaction.message.attachments[0]
                        image_name = attachment.filename # named something like: tmpgtv4qjix1111269940599738479.png
                        # remove .png first
                        partialpathmessageid = image_name[:-4] # should be tmpgtv4qjix1111269940599738479 
                        # extract partialpath, messageid
                        partialpath = partialpathmessageid[:11] # tmpgtv4qjix
                        messageid = partialpathmessageid[11:] # 1111269940599738479
                        # add /tmp/ to partialpath, save as new variable
                        fullpath = "/tmp/" + partialpath # should be /tmp/tmpgtv4qjix
                        #await reaction.message.channel.send(f"✅fullpath extracted, {fullpath}")        
                        emoji = reaction.emoji
                        #await reaction.message.channel.send(f"emojis")  
                        if emoji == "↖️":
                            index = 0
                        elif emoji == "↗️":
                            index = 1
                        elif emoji == "↙️":
                            index = 2
                        elif emoji == "↘️":
                            index = 3 
                            
                        #await reaction.message.channel.send(f"✅index extracted, {index}")         
                        index = index
                        stage_1_result_path = fullpath
                        thread = reaction.message.channel
                        dfif_command_message_id = messageid
                        #await reaction.message.channel.send(f"✅calling dfif2")  
                        await dfif2(index, stage_1_result_path, thread, dfif_command_message_id)

    except Exception as e:
        print(f"Error: {e} (known error, does not cause issues, low priority)")
#------------------------------------------------------------------------------------------------------------------------------------- 
@client.tree.command()
@app_commands.describe(
    prompt='Enter some text to chat with the bot! Like this: /falcon Hello, how are you?')
async def falcon(interaction: discord.Interaction, prompt: str):
    try:  
        global falcon_userid_threadid_dictionary # tracks userid-thread existence
        global instructions
        global threadid_conversation
        global BOT_USER_ID
        global FALCON_CHANNEL_ID

        if interaction.user.id != BOT_USER_ID:
            if interaction.channel.id == FALCON_CHANNEL_ID: 
                await interaction.response.send_message(f"Working on it!")
                channel = interaction.channel
                # 1
                message = await channel.send(f"Creating thread...")
                thread = await message.create_thread(name=f'{prompt}', auto_archive_duration=60)  # interaction.user
                await thread.send(f"[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; The Falcon " \
                f"model and system prompt can be found here: https://huggingface.co/spaces/HuggingFaceH4/falcon-chat]")
                # generation
                chathistory = falconclient.predict( 
                        fn_index=5
                ) # []    
                job = falconclient.submit(prompt, chathistory, instructions, 0.8, 0.9, fn_index=1)  # This is not blocking, similar to run_in_executor (but better)
                while job.done() == False: 
                    status = job.status() 
                    #print(status)
                else:
                    file_paths = job.outputs()
                    full_generation = file_paths[-1] # tmp12345678.json
                with open(full_generation, 'r') as file:
                    data = json.load(file)
                    output_text = data[-1][-1] # we output this as the bot

                threadid_conversation[thread.id] = full_generation
                
                falcon_userid_threadid_dictionary[thread.id] = interaction.user.id
                
                print(output_text)
                await thread.send(f"{output_text}")  

    except Exception as e:
        print(f"Error: {e}")
        #await thread.send(f"{e} cc <@811235357663297546> (falconprivate error)") 
#------------------------------------------------------------------------------------------------------------------------------------- 
async def continue_falcon(message):
    try:
        global instructions
        global threadid_conversation
        await message.add_reaction('<a:loading:1114111677990981692>') 
        chathistory = threadid_conversation[message.channel.id]
        prompt = message.content
        # generation
        job = falconclient.submit(prompt, chathistory, instructions, 0.8, 0.9, fn_index=1)  # This is not blocking, similar to run_in_executor (but better)
        while job.done() == False: 
            status = job.status() 
            #print(status)
        else:
            file_paths = job.outputs()
            full_generation = file_paths[-1] # tmp12345678.json
        with open(full_generation, 'r') as file:
            data = json.load(file)
            output_text = data[-1][-1] # we output this as the bot

        threadid_conversation[message.channel.id] = full_generation # overwrite the old file
        falcon_userid_threadid_dictionary[message.channel.id] = message.author.id
        
        print(output_text)
        await message.reply(f"{output_text}")  
        await message.remove_reaction('<a:loading:1114111677990981692>', client.user) 

    except Exception as e:
        print(f"Error: {e}")
        await message.reply(f"Error: {e} <@811235357663297546> (continue_falcon error)")
#-------------------------------------------------------------------------------------------------------------------------------------
@client.event
async def on_message(message):
    try:
        if not message.author.bot:
            global falcon_userid_threadid_dictionary # tracks userid-thread existence
            if message.channel.id in falcon_userid_threadid_dictionary: # is this a valid thread?
                if falcon_userid_threadid_dictionary[message.channel.id] == message.author.id: # more than that - is this specifically the right user for this thread?
                    # call job for falcon
                    #await message.reply("checks succeeded, calling continue_falcon")
                    await continue_falcon(message)

    except Exception as e:
        print(f"Error: {e}")
#-------------------------------------------------------------------------------------------------------------------------------------
# running in thread
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)

def run_bot():
    client.run(DISCORD_TOKEN)

threading.Thread(target=run_bot).start()

def greet(name):
    return "Hello " + name + "!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.queue(concurrency_count=20)
demo.launch()
