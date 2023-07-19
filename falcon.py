import discord
from discord import app_commands
import gradio as gr
from gradio_client import Client
import os
import asyncio
import json

HF_TOKEN = os.getenv('HF_TOKEN')
falcon_userid_threadid_dictionary = {}
threadid_conversation = {}
# Instructions are for Falcon-chat and can be found here:  https://huggingface.co/spaces/HuggingFaceH4/falcon-chat
instructions = "The following is a conversation between a highly knowledgeable and intelligent AI assistant, called Falcon, and a human user, called User. In the following interactions, User and Falcon will converse in natural language, and Falcon will answer User's questions. Falcon was built to be respectful, polite and inclusive. Falcon was built by the Technology Innovation Institute in Abu Dhabi. Falcon will never decline to answer a question, and always attempts to give an answer that User would be satisfied with. It knows a lot, and always tells the truth. The conversation begins."
falcon_client = Client("HuggingFaceH4/falcon-chat", HF_TOKEN)

BOT_USER_ID = 1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151
FALCON_CHANNEL_ID = 1079459939405279232 if os.getenv("TEST_ENV", False) else 1119313248056004729

async def try_falcon(interaction, prompt):
    """Generates text based on a given prompt"""
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
                message = await channel.send(f"Creating thread...")
                thread = await message.create_thread(name=f'{prompt}', auto_archive_duration=60)  # interaction.user
                await thread.send(f"[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; The Falcon " \
                f"model and system prompt can be found here: https://huggingface.co/spaces/HuggingFaceH4/falcon-chat]")
                
                chathistory = falcon_client.predict(fn_index=5) 
                job = falcon_client.submit(prompt, chathistory, instructions, 0.8, 0.9, fn_index=1)  # This is not blocking, similar to run_in_executor (but better)
                while job.done() is False: 
                    pass
                else:
                    file_paths = job.outputs()
                    full_generation = file_paths[-1]
                with open(full_generation, 'r') as file:
                    data = json.load(file)
                    output_text = data[-1][-1]

                threadid_conversation[thread.id] = full_generation
                falcon_userid_threadid_dictionary[thread.id] = interaction.user.id
                print(output_text)
                await thread.send(f"{output_text}")  

    except Exception as e:
        print(f"Error: {e}")

async def continue_falcon(message):
    """Continues a given conversation based on chathistory"""
    try:
        if not message.author.bot:
            global falcon_userid_threadid_dictionary # tracks userid-thread existence
            if message.channel.id in falcon_userid_threadid_dictionary: # is this a valid thread?
                 if falcon_userid_threadid_dictionary[message.channel.id] == message.author.id: # more than that - is this specifically the right user for this thread?
                    global instructions
                    global threadid_conversation
                    await message.add_reaction('🔁') 
                    chathistory = threadid_conversation[message.channel.id]
                    prompt = message.content

                    job = falcon_client.submit(prompt, chathistory, instructions, 0.8, 0.9, fn_index=1)
                    while job.done() is False: 
                        pass
                    else:
                        file_paths = job.outputs()
                        full_generation = file_paths[-1]
                    with open(full_generation, 'r') as file:
                        data = json.load(file)
                        output_text = data[-1][-1]
            
                    threadid_conversation[message.channel.id] = full_generation # overwrite the old file
                    falcon_userid_threadid_dictionary[message.channel.id] = message.author.id
                    print(output_text)
                    await message.reply(f"{output_text}")  

    except Exception as e:
        print(f"Error: {e}")
        await message.reply(f"Error: {e} <@811235357663297546> (continue_falcon error)")        
