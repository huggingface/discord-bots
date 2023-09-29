import asyncio
import json
import os
import threading
from threading import Event

import discord
import gradio as gr
from discord.ext import commands
from gradio_client import Client

event = Event()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
codellama_client = Client("https://huggingface-projects-codellama-13b-chat.hf.space/", HF_TOKEN)
codellama_threadid_userid_dictionary = {}
codellama_threadid_conversation = {}
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    synced = await bot.tree.sync()
    print(f"Synced commands: {', '.join([s.name for s in synced])}.")
    event.set()
    print("------")


@bot.hybrid_command(
    name="codellama",
    description="Enter a prompt to generate code!",
)
async def codellama(ctx, prompt: str):
    """Codellama generation"""
    try:
        await try_codellama(ctx, prompt)
    except Exception as e:
        print(f"Error: {e}")


@bot.event
async def on_message(message):
    """Checks channel and continues codellama conversation if it's the right Discord Thread"""
    try:
        if not message.author.bot:
            await continue_codellama(message)
    except Exception as e:
        print(f"Error: {e}")


async def try_codellama(ctx, prompt):
    """Generates code based on a given prompt"""
    try:
        global codellama_threadid_userid_dictionary
        global codellama_threadid_conversation

        message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
        thread = await message.create_thread(name=prompt[:100])

        loop = asyncio.get_running_loop()
        output_code = await loop.run_in_executor(None, codellama_initial_generation, prompt, thread)
        codellama_threadid_userid_dictionary[thread.id] = ctx.author.id

        print(output_code)
        await thread.send(output_code)
    except Exception as e:
        print(f"Error: {e}")


def codellama_initial_generation(prompt, thread):
    """Job.submit inside of run_in_executor = more consistent bot behavior"""
    global codellama_threadid_conversation

    chat_history = f"{thread.id}.json"
    conversation = []
    with open(chat_history, "w") as json_file:
        json.dump(conversation, json_file)

    job = codellama_client.submit(prompt, chat_history, fn_index=0)

    while job.done() is False:
        pass
    else:
        result = job.outputs()[-1]
        with open(result, "r") as json_file:
            data = json.load(json_file)
        response = data[-1][-1]
        conversation.append((prompt, response))
        with open(chat_history, "w") as json_file:
            json.dump(conversation, json_file)

        codellama_threadid_conversation[thread.id] = chat_history
        if len(response) > 1300:
            response = response[:1300] + "...\nTruncating response due to discord api limits."
        return response


async def continue_codellama(message):
    """Continues a given conversation based on chat_history"""
    try:
        if not message.author.bot:
            global codellama_threadid_userid_dictionary  # tracks userid-thread existence
            if message.channel.id in codellama_threadid_userid_dictionary:  # is this a valid thread?
                if codellama_threadid_userid_dictionary[message.channel.id] == message.author.id:
                    global codellama_threadid_conversation

                    prompt = message.content
                    chat_history = codellama_threadid_conversation[message.channel.id]

                    # Check to see if conversation is ongoing or ended (>15000 characters)
                    with open(chat_history, "r") as json_file:
                        conversation = json.load(json_file)
                    total_characters = 0
                    for item in conversation:
                        for string in item:
                            total_characters += len(string)

                    if total_characters < 15000:
                        job = codellama_client.submit(prompt, chat_history, fn_index=0)
                        while job.done() is False:
                            pass
                        else:
                            result = job.outputs()[-1]
                            with open(result, "r") as json_file:
                                data = json.load(json_file)
                            response = data[-1][-1]
                            with open(chat_history, "r") as json_file:
                                conversation = json.load(json_file)
                            conversation.append((prompt, response))
                            with open(chat_history, "w") as json_file:
                                json.dump(conversation, json_file)
                            codellama_threadid_conversation[message.channel.id] = chat_history

                            if len(response) > 1300:
                                response = response[:1300] + "...\nTruncating response due to discord api limits."

                            await message.reply(response)

                            total_characters = 0
                            for item in conversation:
                                for string in item:
                                    total_characters += len(string)

                            if total_characters >= 15000:
                                await message.reply("Conversation ending due to length, feel free to start a new one!")

    except Exception as e:
        print(f"Error: {e}")


def run_bot():
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN NOT SET")
        event.set()
    else:
        bot.run(DISCORD_TOKEN)


threading.Thread(target=run_bot).start()
event.wait()

welcome_message = """
## Add this bot to your server by clicking this link: 

https://discord.com/api/oauth2/authorize?client_id=1152238037355474964&permissions=309237647360&scope=bot

## How to use it?

The bot can be triggered via `/codellama` followed by your text prompt.

This will generate text based on the text prompt and create a thread for the discussion.

To continue the conversation, simply ask additional questions in the thread - no need for repeating the command!

⚠️ Note ⚠️: Please make sure this bot's command does have the same name as another command in your server.

⚠️ Note ⚠️: Bot commands do not work in DMs with the bot as of now.
"""


with gr.Blocks() as demo:
    gr.Markdown(f"""
    # Discord bot of https://huggingface.co/spaces/codellama/codellama-13b-chat
    {welcome_message}
    """)

demo.launch()
