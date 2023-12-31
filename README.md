# Our bots 🤖
| Bot | Code Link | Invite Link |
| -------- | -------- | -------- |
| CodeLlama 13B   | [Code](https://huggingface.co/spaces/huggingface-projects/codellama-bot)   | [Invite Bot](https://discord.com/api/oauth2/authorize?client_id=1152238037355474964&permissions=309237647360&scope=bot)   |
| DeepFloydIF  | [Code](https://huggingface.co/spaces/huggingface-projects/deepfloydif-bot)   | [Invite Bot](https://discord.com/api/oauth2/authorize?client_id=1154395078735953930&permissions=51200&scope=bot)   |
| Falcon 180B  | [Code](https://huggingface.co/spaces/huggingface-projects/falcon180b-bot)   | [Invite Bot](https://discord.com/api/oauth2/authorize?client_id=1155169841276260546&permissions=326417516544&scope=bot)   |
| Wuerstchen  | [Code](https://huggingface.co/spaces/huggingface-projects/wuerstchen-bot)   | [Invite Bot](https://discord.com/api/oauth2/authorize?client_id=1155489509518098565&permissions=51200&scope=bot)   |
| AudioLDM 2  | [Code](https://huggingface.co/spaces/huggingface-projects/AudioLDM2-bot)| - |
| MusicGen | [Code](https://huggingface.co/spaces/huggingface-projects/MusicGen-bot) | - |


# TLDR: How do our bots work ❓

- We run the bots inside a free-tier [Space](https://huggingface.co/new-space?sdk=gradio), which acts as a server. 
- We use Gradio apps as APIs to use them in our bots

### Building blocks of a Discord Bot 🤖

1. Create an [application](https://discord.com/developers/applications)
2. Create a Hugging Face [Space](https://huggingface.co/new-space?sdk=gradio)
3. Add [commands](https://huggingface.co/spaces/huggingface-projects/huggingbots/blob/main/app.py)

After that, we'll have a working discord bot. So how do we spice it up with machine learning?

### Using ML demos in your bot 🧠
- Almost any [Gradio](https://github.com/gradio-app/gradio/tree/main/client/python) app can be [used as an API](https://www.gradio.app/guides/sharing-your-app#api-page)! This means we can query most Spaces on the Hugging Face Hub and use them in our discord bots.

  ![image](https://github.com/lunarflu/fork-discord-bots/assets/70143200/97316c28-7c99-42c0-ab6a-687819d678f8)


Here's an extremely simplified example 💻: 

```python
from gradio_client import Client

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

```
In summary, we:
1. Use a command and specify a prompt ("piano music", for example)
2. Query a specific Gradio Space as an API, and send it our prompt
3. Retrieve the results once done and post them to discord

🎉 And voila! 🎉

For further explorations (depending on your needs), we can recommend checking these out 🧐:
- Events in discord bots (to automate some behavior)
- Handling concurrency (important if you're making many concurrent requests at once)
- UI (discord buttons, interactive fields) (can add a lot of functionality)
