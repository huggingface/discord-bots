import asyncio
import json
import os

from gradio_client import Client

HF_TOKEN = os.getenv("HF_TOKEN")

codellama = Client("https://huggingface-projects-codellama-13b-chat.hf.space/", HF_TOKEN)

BOT_USER_ID = 1102236653545861151  # real
CODELLAMA_CHANNEL_ID = 1100458786826747945  # bot-test


codellama_threadid_userid_dictionary = {}
codellama_threadid_conversation = {}


def codellama_initial_generation(prompt, thread):
    """job.submit inside of run_in_executor = more consistent bot behavior"""
    global codellama_threadid_conversation

    chat_history = f"{thread.id}.json"
    conversation = []
    with open(chat_history, "w") as json_file:
        json.dump(conversation, json_file)

    job = codellama.submit(prompt, chat_history, fn_index=0)

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


async def try_codellama(ctx, prompt):
    """Generates text based on a given prompt"""
    try:
        global codellama_threadid_userid_dictionary  # tracks userid-thread existence
        global codellama_threadid_conversation

        if ctx.author.id != BOT_USER_ID:
            if ctx.channel.id == CODELLAMA_CHANNEL_ID:
                message = await ctx.send(f"**{prompt}** - {ctx.author.mention}")
                if len(prompt) > 99:
                    small_prompt = prompt[:99]
                else:
                    small_prompt = prompt
                thread = await message.create_thread(name=small_prompt, auto_archive_duration=60)

                loop = asyncio.get_running_loop()
                output_code = await loop.run_in_executor(None, codellama_initial_generation, prompt, thread)
                codellama_threadid_userid_dictionary[thread.id] = ctx.author.id

                print(output_code)
                await thread.send(output_code)
    except Exception as e:
        print(f"try_codellama Error: {e}")
        await ctx.send(f"Error: {e} <@811235357663297546> (try_codellama error)")


async def continue_codellama(message):
    """Continues a given conversation based on chat_history"""
    try:
        if not message.author.bot:
            global codellama_threadid_userid_dictionary  # tracks userid-thread existence
            if message.channel.id in codellama_threadid_userid_dictionary:  # is this a valid thread?
                if codellama_threadid_userid_dictionary[message.channel.id] == message.author.id:
                    print("Safetychecks passed for continue_codellama")
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
                        if os.environ.get("TEST_ENV") == "True":
                            print("Running codellama.submit")
                        job = codellama.submit(prompt, chat_history, fn_index=0)
                        while job.done() is False:
                            pass
                        else:
                            if os.environ.get("TEST_ENV") == "True":
                                print("Continue_codellama job done")

                            result = job.outputs()[-1]
                            with open(result, "r") as json_file:
                                data = json.load(json_file)
                            response = data[-1][-1]

                            with open(chat_history, "r") as json_file:
                                conversation = json.load(json_file)   

                            conversation.append((prompt, response))
                            # now we have prompt, response, and the newly updated full conversation

                            with open(chat_history, "w") as json_file:
                                json.dump(conversation, json_file)
                            if os.environ.get("TEST_ENV") == "True":
                                print(prompt)
                                print(response)
                                print(conversation)
                                print(chat_history)

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
        print(f"continue_codellama Error: {e}")
        await message.reply(f"Error: {e} <@811235357663297546> (continue_codellama error)")
