import discord
import sys
import os
import threading
from typing import NamedTuple
from discord import app_commands
from datetime import datetime
from configparser import ConfigParser
config = ConfigParser()
#target_channel = discord.get_channel("944054272348278827")

with open('token.txt', 'r') as file:
    TOKEN = file.read().replace('\n', '')

with open('guild.txt', 'r') as file:
    GUILD = int(file.read().replace('\n', ''))


class UserSettings():
    ckpt: str
    lastprompt: str
    samples: str
    quantity: str

class processJob():
    user: str
    prompt: UserSettings
    priority: int

processQueue = []

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
txt2img = "./scripts/txt2img.py"
now = datetime.now()
sd_updates = client.get_channel(GUILD)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await tree.sync(guild=discord.Object(id=GUILD))
    print("Ready!")
 
@client.event
async def on_message(message):
    if message.author == client.user:
        return


#Samples setting
@tree.command(name = "samples", description = "Sets number of samples.", guild=discord.Object(GUILD)) 

async def sd(interaction: discord.Interaction, samples: str):
    print("1")
    current_time = now.strftime("%H:%M:%S")
    user = interaction.user
    currentUserSettings = readConfig(str(user))
    print("2")
    currentUserSettings.samples = samples
    updateConfig(str(user), currentUserSettings)
    await interaction.response.send_message(user.mention + " updated samples.")
    await interaction.user.send("Updated samples to " + samples + ".")

#StashPrompt 
@tree.command(name = "stash", description = "Saves the last prompt (try /saved)", guild=discord.Object(GUILD)) 

async def sd(interaction: discord.Interaction):
    user = interaction.user
    currentUserSettings = readConfig(str(user))
    promtToStash = currentUserSettings.lastprompt
    stashPrompt(str(user), currentUserSettings)
    await interaction.response.send_message(user.mention + " stashed prompt '" + currentUserSettings.lastprompt + ",' using the model '" + currentUserSettings.ckpt + "' with " + currentUserSettings.samples + " samples.")

#SavedPrompt 
@tree.command(name = "saved", description = "Views your saved prompts", guild=discord.Object(GUILD)) 

async def sd(interaction: discord.Interaction):
    user = str(interaction.user)
    currentUserSettings = readConfig(user)

    with open('sdout/' + user + '/config/stashed.txt') as file:
        stashedArray = file.readlines()
        formattedMessage = "Hello " + user + ", here are the prompts you stashed:\n```"
        for prompt in stashedArray:
            formattedMessage = formattedMessage + "\n" + prompt
        formattedMessage = formattedMessage + "```"
    await interaction.user.send(formattedMessage)
    await interaction.response.send_message(interaction.user.mention  + "saved prompts in your DMs.")


    
        

#default SD command to generate an image
@tree.command(name = "sd", description = "Test Command", guild=discord.Object(GUILD)) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def sd(interaction: discord.Interaction, prompt: str):
   


    current_time = now.strftime("%H:%M:%S")
    print(interaction.user)
    user = str(interaction.user)


    isExist = os.path.exists("sdout/"+user)
    # Create config
    if not isExist:
        os.makedirs("sdout/"+user)
        os.makedirs("sdout/"+user+'/config')
        nf = open('sdout/'+user+'/config/config.ini', 'x')
        nf.close()
        defaultConfigLines = ["[user]", "\n", "ckpt = midjourney.ckpt", "\n", "lastprompt = none","\n", "samples = 20", "\n", "quantity = 1"]
        newConfig = open('sdout/'+ user + '/config/config.ini', 'w')
        newConfig.writelines(defaultConfigLines)
        newConfig.close()

    # Read config
    if isExist:
        config.read('sdout/'+user+'/config/config.ini')
        currentUser = UserSettings()
        currentUser.ckpt = config.get('user', 'ckpt')
        currentUser.lastprompt = config.get('user', 'lastprompt')
        currentUser.samples = config.get('user', 'samples')
        currentUser.quantity = config.get('user', 'quantity')
        #Check for max iamges
        if int(currentUser.quantity) > 10:
            currentUser.quantity = '10'

        currentUser = readConfig(user)
        currentUser.lastprompt = prompt
        updateConfig(user, currentUser)
    await interaction.response.send_message(interaction.user.mention + " started a job for ```" + prompt + "```\nUsing " + "```" + currentUser.ckpt + ", " + currentUser.samples + " samples, " + currentUser.quantity + " image(s) ""```" + current_time)

    t1 = threading.Thread(target=genImagePlusHandle,args=(interaction, prompt, 'midjourney.ckpt','1'))
    t1.start()
    


# not working so far, mainly called by SD threads
def genImagePlusHandle(interaction, prompt, ckpt, samples):
        os.system('python ./scripts/txt2img.py --prompt ' + '"' + prompt + '"' + ' --plms --ckpt ./models/Stable-diffusion/' + ckpt + ' --skip_grid --n_samples ' + samples + " --n_iter 1")
        interaction.user.send('Image gen done')

# Reads user config file and returns the Class.
def readConfig(user):
    config.read('sdout/'+user+'/config/config.ini')
    theReadConfig = UserSettings()
    theReadConfig.ckpt = config.get('user', 'ckpt')
    theReadConfig.lastprompt = config.get('user', 'lastprompt')
    theReadConfig.samples = config.get('user', 'samples')
    theReadConfig.quantity = config.get('user', 'quantity')
    return theReadConfig

# Update the user's config file
def updateConfig(user, currentUserSettings):
    configFile = open("sdout/" + user + "/config/config.ini", 'w')
    configFile.writelines("[user]" + "\n" + "ckpt = " + currentUserSettings.ckpt + "\n" + "lastprompt = " + currentUserSettings.lastprompt + "\n" + "samples = " + currentUserSettings.samples + "\n" + "quantity = " + currentUserSettings.quantity + "\n")
    print("Updated " + user + "'s config file.")

#Stash last prompt
def stashPrompt(user, currentUserSettings):
    isExist = os.path.exists("sdout/"+user+"/config/stashed.txt")
    if not isExist:
        nf = open('sdout/'+user+'/config/stashed.txt', 'x')
        nf.close()

    configFile = open("sdout/" + user + "/config/stashed.txt", 'a')
    configFile.writelines(currentUserSettings.lastprompt + " | Using " + currentUserSettings.ckpt + " " + " " + currentUserSettings.samples + " samples \n")
    configFile.close()


async def list_models(Interaction):
    models = os.listdir('./models/Stable-diffusion')
    await Interaction.response.send_message(Interaction.user.mention + " here's the availible models:" + models)


#Adds a job to the process queue, in progress rn UPDATE TOMORROW TO REPLACE MULTITHREADING CORRECTLY
async def addProcessQueue(user,currentUserSettings):
    newJob = processJob()
    newJob.user = user
    newJob.prompt = currentUserSettings
    newJob.priority = 1
client.run(TOKEN)
#client.run('MTA2NDAwMTE5NzUxNTczNTA3MQ.G3HFFn.-5paqzNfFGQk8TnQjVNkHQPSt8Urpe-prtl20A')


