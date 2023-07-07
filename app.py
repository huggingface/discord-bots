import discord
from discord import app_commands
import gradio_client
import gradio as gr
from gradio_client import Client
import os
import threading 
import json
import random
from PIL import Image
import asyncio
import glob

# HF GUILD SETTINGS
MY_GUILD_ID = 1077674588122648679 if os.getenv("TEST_ENV", False) else 879548962464493619
MY_GUILD = discord.Object(id=MY_GUILD_ID)
HF_TOKEN = os.getenv('HF_TOKEN')
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)

falcon_userid_threadid_dictionary = {}
threadid_conversation = {}
GUILD_ID = 1077674588122648679 if os.getenv("TEST_ENV", False) else 879548962464493619
FALCON_CHANNEL_ID = 1079459939405279232 if os.getenv("TEST_ENV", False) else 1119313248056004729
DEEPFLOYD_CHANNEL_ID = 1121834257959092234 if os.getenv("TEST_ENV", False) else 1119313215675973714
BOT_USER_ID = 1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151

deepfloyd_client = Client("huggingface-projects/IF", HF_TOKEN)
falcon_client = Client("HuggingFaceH4/falcon-chat", HF_TOKEN)
# Instructions are for Falcon-chat and can be found here:  https://huggingface.co/spaces/HuggingFaceH4/falcon-chat
instructions = "The following is a conversation between a highly knowledgeable and intelligent AI assistant, called Falcon, and a human user, called User. In the following interactions, User and Falcon will converse in natural language, and Falcon will answer User's questions. Falcon was built to be respectful, polite and inclusive. Falcon was built by the Technology Innovation Institute in Abu Dhabi. Falcon will never decline to answer a question, and always attempts to give an answer that User would be satisfied with. It knows a lot, and always tells the truth. The conversation begins."

class MyClient(discord.Client):
    """This structure allows commands to work instantly (instead of needing to sync global commands for up to an hour)"""
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to our guild
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

client = MyClient(intents=discord.Intents.default())

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------') 
 
def deepfloyd_stage1(prompt):
    """Generates an image based on a prompt"""
    negative_prompt = ''
    seed = random.randint(0, 1000)
    number_of_images = 4
    guidance_scale = 7
    custom_timesteps_1 = 'smart50'
    number_of_inference_steps = 50
    
    stage_1_results, stage_1_param_path, stage_1_result_path = deepfloyd_client.predict(prompt, negative_prompt, seed, number_of_images, guidance_scale, custom_timesteps_1, number_of_inference_steps, api_name='/generate64')
    
    return [stage_1_results, stage_1_param_path, stage_1_result_path]        

def deepfloyd_stage2(index, stage_1_result_path):
    """Upscales one of the images from deepfloyd_stage1 based on the chosen index"""
    selected_index_for_stage_2 = index
    seed_2 = 0
    guidance_scale_2 = 4
    custom_timesteps_2 = 'smart50'
    number_of_inference_steps_2 = 50
    result_path = deepfloyd_client.predict(stage_1_result_path, selected_index_for_stage_2, seed_2, guidance_scale_2, custom_timesteps_2, number_of_inference_steps_2, api_name='/upscale256')
    return result_path    

async def react_1234(reaction_emojis, combined_image_dfif):
    """Sets up 4 reaction emojis so the user can choose an image to upscale for deepfloydif"""
    for emoji in reaction_emojis:
        await combined_image_dfif.add_reaction(emoji) 
        
@client.tree.command()
@app_commands.describe(
    prompt='Enter a prompt to generate an image! Can generate realistic text, too!')
async def deepfloydif(interaction: discord.Interaction, prompt: str):
    """DeepfloydIF command (generate images with realistic text using slash commands)"""
    thread = None
    try:
        global BOT_USER_ID
        global DEEPFLOYD_CHANNEL_ID
        if interaction.user.id != BOT_USER_ID:
            if interaction.channel.id == DEEPFLOYD_CHANNEL_ID:
                await interaction.response.send_message(f"Working on it!")
                channel = interaction.channel
                # interaction.response message can't be used to create a thread, so we create another message
                message = await channel.send(f"DeepfloydIF Thread")
                await message.add_reaction('<a:loading:1114111677990981692>')
                thread = await message.create_thread(name=f'{prompt}', auto_archive_duration=60) 
                await thread.send(f"[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; Additional information" \
                f" on the DeepfloydIF model can be found here: https://huggingface.co/spaces/DeepFloyd/IF")

                dfif_command_message_id = message.id # used for updating the 'status' of our generations using reaction emojis
                
                await thread.send(f'{interaction.user.mention}Generating images in thread, can take ~1 minute...')

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, deepfloyd_stage1, prompt)  
                stage_1_results = result[0]
                stage_1_result_path = result[2]
                partial_path = stage_1_result_path[5:]
                png_files = list(glob.glob(f"{stage_1_results}/**/*.png"))

                if png_files:
                    # take all 4 images and combine them into one large 2x2 image (similar to Midjourney)
                    png_file_index = 0
                    images = load_image(png_files, stage_1_results, png_file_index) 
                    combined_image = Image.new('RGB', (images[0].width * 2, images[0].height * 2))
                    combined_image.paste(images[0], (0, 0))
                    combined_image.paste(images[1], (images[0].width, 0))
                    combined_image.paste(images[2], (0, images[0].height))
                    combined_image.paste(images[3], (images[0].width, images[0].height))
                    combined_image_path = os.path.join(stage_1_results, f'{partial_path}{dfif_command_message_id}.png')
                    combined_image.save(combined_image_path)

                    with open(combined_image_path, 'rb') as f:
                        combined_image_dfif = await thread.send(f'{interaction.user.mention} React with the image number you want to upscale!', file=discord.File(f, f'{partial_path}{dfif_command_message_id}.png'))                

                    emoji_list = ['↖️', '↗️', '↙️', '↘️']
                    await react_1234(emoji_list, combined_image_dfif)
                    await message.remove_reaction('<a:loading:1114111677990981692>', client.user)
                    await message.add_reaction('<:agree:1098629085955113011>')
                else:
                    await thread.send(f'{interaction.user.mention} No PNG files were found, cannot post them!')

    except Exception as e:
        print(f"Error: {e}")
        await message.remove_reaction('<a:loading:1114111677990981692>', client.user)
        await message.add_reaction('<:disagree:1098628957521313892>')
        #await thread.send(f"Error: {e} <@811235357663297546> (continue_falcon error)")

def load_image(png_files, stage_1_results, png_file_index):
    """Opens images as variables so we can combine them later"""
    for file in png_files:
        png_file = png_files[png_file_index]
        png_path = os.path.join(stage_1_results, png_file)
        if png_file_index == 0:
            img1 = Image.open(png_path)
        if png_file_index == 1:
            img2 = Image.open(png_path)
        if png_file_index == 2:
            img3 = Image.open(png_path)
        if png_file_index == 3:
            img4 = Image.open(png_path)
        png_file_index = png_file_index + 1
    return [img1, img2, img3, img4]

async def dfif2(index: int, stage_1_result_path, thread, dfif_command_message_id): 
    """upscaling function for images generated using /deepfloydif"""
    try:
        parent_channel = thread.parent
        dfif_command_message = await parent_channel.fetch_message(dfif_command_message_id)
        await dfif_command_message.remove_reaction('<:agree:1098629085955113011>', client.user)
        await dfif_command_message.add_reaction('<a:loading:1114111677990981692>')
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
        result_path = await loop.run_in_executor(None, deepfloyd_stage2, index, stage_1_result_path) 
        
        with open(result_path, 'rb') as f:
            await thread.send('Here is the upscaled image!', file=discord.File(f, 'result.png'))
            
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
        await thread.edit(archived=True)

@client.event
async def on_reaction_add(reaction, user): 
    """Checks for a reaction in order to call dfif2"""
    try:
        global BOT_USER_ID
        global DEEPFLOYD_CHANNEL_ID
        if user.id != BOT_USER_ID: # 
            thread = reaction.message.channel
            thread_parent_id = thread.parent.id
            if thread_parent_id == DEEPFLOYD_CHANNEL_ID: 
                if reaction.message.attachments:
                    if user.id == reaction.message.mentions[0].id: 
                        attachment = reaction.message.attachments[0]
                        image_name = attachment.filename 
                        partial_path_message_id = image_name[:-4] 
                        partial_path = partial_path_message_id[:11] 
                        message_id = partial_path_message_id[11:] 
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
                        stage_1_result_path = full_path
                        thread = reaction.message.channel
                        dfif_command_message_id = message_id
                        await dfif2(index, stage_1_result_path, thread, dfif_command_message_id)

    except Exception as e:
        print(f"Error: {e} (known error, does not cause issues, low priority)")
 
@client.tree.command()
@app_commands.describe(
    prompt='Enter some text to chat with the bot! Like this: /falcon Hello, how are you?')
async def falcon(interaction: discord.Interaction, prompt: str):
    """Generates text based on a given prompt"""
    try:  
        global falcon_userid_threadid_dictionary # tracks userid-thread existence
        global instructions
        global threadid_conversation
        global BOT_USER_ID
        global FALCON_CHANNEL_ID

        if interaction.user.id != BOT_USER_ID:
            if interaction.channel.id == FALCON_CHANNEL_ID: 
                await interaction.response.send_message("Working on it!")
                channel = interaction.channel
                message = await channel.send("Creating thread...")
                thread = await message.create_thread(name=f'{prompt}', auto_archive_duration=60)  # interaction.user
                await thread.send("[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; The Falcon model and system prompt can be found here: https://huggingface.co/spaces/HuggingFaceH4/falcon-chat]")

                chat_history = falcon_client.predict( 
                        fn_index=5
                ) # []    
                job = falcon_client.submit(prompt, chat_history, instructions, 0.8, 0.9, fn_index=1)  # This is not blocking, similar to run_in_executor (but better)
                while job.done() is False: 
                    pass 
                else:
                    file_paths = job.outputs()
                    full_generation = file_paths[-1]
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

async def continue_falcon(message):
    """Continues a given conversation based on chathistory"""
    try:
        global instructions
        global threadid_conversation
        await message.add_reaction('<a:loading:1114111677990981692>') 
        chathistory = threadid_conversation[message.channel.id]
        prompt = message.content

        job = falcon_client.submit(prompt, chathistory, instructions, 0.8, 0.9, fn_index=1)  # This is not blocking, similar to run_in_executor (but better)
        while job.done() is False: 
            pass 
        else:
            file_paths = job.outputs()
            full_generation = file_paths[-1]
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

@client.event
async def on_message(message):
    """Detects messages and calls continue_falcon if we're in the right channel"""
    try:
        if not message.author.bot:
            global falcon_userid_threadid_dictionary # tracks userid-thread existence
            if message.channel.id in falcon_userid_threadid_dictionary: # is this a valid thread?
                if falcon_userid_threadid_dictionary[message.channel.id] == message.author.id: # more than that - is this specifically the right user for this thread?
                    await continue_falcon(message)

    except Exception as e:
        print(f"Error: {e}")

# running in thread
def run_bot():
    client.run(DISCORD_TOKEN)

threading.Thread(target=run_bot).start()

def greet(name):
    return "Hello " + name + "!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.queue(concurrency_count=20)
demo.launch()
