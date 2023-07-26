from gradio_client import Client
import os
import asyncio
import json
from concurrent.futures import wait

HF_TOKEN = os.getenv("HF_TOKEN")
falcon_userid_threadid_dictionary = {}
threadid_conversation = {}
# Instructions are for Falcon-chat and can be found here:  https://huggingface.co/spaces/HuggingFaceH4/falcon-chat
instructions = "The following is a conversation between a highly knowledgeable and intelligent AI assistant, called Falcon, and a human user, called User. In the following interactions, User and Falcon will converse in natural language, and Falcon will answer User's questions. Falcon was built to be respectful, polite and inclusive. Falcon was built by the Technology Innovation Institute in Abu Dhabi. Falcon will never decline to answer a question, and always attempts to give an answer that User would be satisfied with. It knows a lot, and always tells the truth. The conversation begins."
falcon_client = Client("HuggingFaceH4/falcon-chat", HF_TOKEN)

BOT_USER_ID = (
    1086256910572986469 if os.getenv("TEST_ENV", False) else 1102236653545861151
)
FALCON_CHANNEL_ID = (
    1079459939405279232 if os.getenv("TEST_ENV", False) else 1119313248056004729
)


def falcon_initial_generation(prompt, instructions, thread):
    """Solves two problems at once; 1) The Slash command + job.submit interaction, and 2) the need for job.submit in order to locate the full generated text"""
    global threadid_conversation

    chathistory = falcon_client.predict(fn_index=5)
    temperature = 0.8
    p_nucleus_sampling = 0.9

    job = falcon_client.submit(
        prompt, chathistory, instructions, temperature, p_nucleus_sampling, fn_index=1
    )
    wait([job])
    if os.environ.get("TEST_ENV") == "True":
        print("falcon text gen job done")
    file_paths = job.outputs()
    print(file_paths)
    full_generation = file_paths[-1]
    print(full_generation)
    with open(full_generation, "r") as file:
        data = json.load(file)
        print(data)
    output_text = data[-1][-1]
    threadid_conversation[thread.id] = full_generation
    if len(output_text) > 1300:
        output_text = (
            output_text[:1300]
            + "...\nTruncating response to 2000 characters due to discord api limits."
        )
    if os.environ.get("TEST_ENV") == "True":
        print(output_text)
    return output_text


async def try_falcon(interaction, prompt):
    """Generates text based on a given prompt"""
    try:
        global falcon_userid_threadid_dictionary  # tracks userid-thread existence
        global threadid_conversation

        if interaction.user.id != BOT_USER_ID:
            if interaction.channel.id == FALCON_CHANNEL_ID:
                if os.environ.get("TEST_ENV") == "True":
                    print("Safetychecks passed for try_falcon")
                await interaction.response.send_message("Working on it!")
                channel = interaction.channel
                message = await channel.send("Creating thread...")
                thread = await message.create_thread(
                    name=prompt, auto_archive_duration=60
                )  # interaction.user
                await thread.send(
                    "[DISCLAIMER: HuggingBot is a **highly experimental** beta feature; The Falcon model and system prompt can be found here: https://huggingface.co/spaces/HuggingFaceH4/falcon-chat]"
                )

                if os.environ.get("TEST_ENV") == "True":
                    print("Running falcon_initial_generation...")
                loop = asyncio.get_running_loop()
                output_text = await loop.run_in_executor(
                    None, falcon_initial_generation, prompt, instructions, thread
                )
                falcon_userid_threadid_dictionary[thread.id] = interaction.user.id

                await thread.send(output_text)
    except Exception as e:
        print(f"try_falcon Error: {e}")


async def continue_falcon(message):
    """Continues a given conversation based on chathistory"""
    try:
        if not message.author.bot:
            global falcon_userid_threadid_dictionary  # tracks userid-thread existence
            if (
                message.channel.id in falcon_userid_threadid_dictionary
            ):  # is this a valid thread?
                if (
                    falcon_userid_threadid_dictionary[message.channel.id]
                    == message.author.id
                ):  # more than that - is this specifically the right user for this thread?
                    if os.environ.get("TEST_ENV") == "True":
                        print("Safetychecks passed for continue_falcon")
                    global instructions
                    global threadid_conversation
                    await message.add_reaction("🔁")

                    prompt = message.content
                    chathistory = threadid_conversation[message.channel.id]
                    temperature = 0.8
                    p_nucleus_sampling = 0.9

                    if os.environ.get("TEST_ENV") == "True":
                        print("Running falcon_client.submit")
                    job = falcon_client.submit(
                        prompt,
                        chathistory,
                        instructions,
                        temperature,
                        p_nucleus_sampling,
                        fn_index=1,
                    )
                    wait([job])
                    if os.environ.get("TEST_ENV") == "True":
                        print("Continue_falcon job done")
                    file_paths = job.outputs()
                    full_generation = file_paths[-1]
                    with open(full_generation, "r") as file:
                        data = json.load(file)
                        output_text = data[-1][-1]
                    threadid_conversation[
                        message.channel.id
                    ] = full_generation  # overwrite the old file
                    if len(output_text) > 1300:
                        output_text = (
                            output_text[:1300]
                            + "...\nTruncating response to 2000 characters due to discord api limits."
                        )
                    await message.reply(output_text)
    except Exception as e:
        print(f"continue_falcon Error: {e}")
        await message.reply(f"Error: {e} <@811235357663297546> (continue_falcon error)")
