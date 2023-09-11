# How do our bots work?

We run the bots inside a free-tier [Space](https://huggingface.co/new-space), which acts as a server. 


-> Instructions on having their own bots
# Building blocks of bots

-> The discord end (an application associated with a discord account)
https://discord.com/developers/applications
-> HF Space (to host the bot for free)

-> Commands (to make the bot do something)
-> Events (to automate some behavior)

# Using ML demos in your bot
-> Almost any Gradio app can be [used as an API](https://www.gradio.app/guides/sharing-your-app#api-page)! This means we can query most Spaces on the Hugging Face Hub and use them in our discord bots. 
-> Handling concurrency

Here's a simplified example: 

    # query space
    musicgen = Client("huggingface-projects/transformers-musicgen", hf_token=os.getenv("HF_TOKEN"))

    # call this function when we use a command + prompt
    async def music_create(ctx, prompt): 
    
        # run_in_executor for the blocking function
        loop = asyncio.get_running_loop()
        job = await loop.run_in_executor(None, music_create_job, prompt)

        # extract what we want from the outputs
        video = job.outputs()[0][0]
        
        # send what we want to discord
        await thread.send(video_file)


    # submit as a Gradio job; this makes retrieving outputs simpler
    def music_create_job(prompt):
    
        # pass prompt and other parameters if necessary
        job = musicgen.submit(prompt, api_name="/predict")
        return job
