# bot.py test12
#test
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
import pdb
from openai import OpenAI
from db import supabase

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# # There should be a file called 'tokens.json' inside the same folder as this file
# token_path = 'tokens.json'
# if not os.path.isfile(token_path):
#     raise Exception(f"{token_path} not found!")
# with open(token_path) as f:
#     # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
#     tokens = json.load(f)
#     discord_token = tokens['discord']

# Load the discord token from environment variable
discord_token = os.getenv('DISCORD_TOKEN')
openai_key = os.getenv('OPENAI_KEY')
openai_client = OpenAI(api_key=openai_key)

class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {} # Map from user IDs to the state of their review

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel


    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        '''
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message, self.mod_channels)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if message.channel.name == f'group-{self.group_num}-mod':
            if message.content == Review.HELP_KEYWORD:
                reply =  "Use the `review` command to begin the reporting process.\n"
                reply += "Use the `cancel` command to cancel the report process.\n"
                await message.channel.send(reply)
            
            author_id = message.author.id
            responses = []

            # Only respond to messages if they're part of a review flow
            if author_id not in self.reviews and not message.content.startswith(Review.START_KEYWORD):
                return

            # If we don't currently have an active review for this user, add one
            if author_id not in self.reviews:
                self.reviews[author_id] = Review(self)
            
            # Let the review class handle this message; forward all the messages it returns to us
            responses = await self.reviews[author_id].handle_channel_message(message)
            for r in responses:
                await message.channel.send(r)
            
            # If the review is complete or cancelled, remove it from our map
            if self.reviews[author_id].review_complete():
                self.reviews.pop(author_id)

        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # WZHAI: Changed from message.content to message to include the images
        scores = self.eval_text(message)
        if scores == "This message contains animal abuse.":
            data = {
                "authorId": message.author.id,
                "authorUserName": message.author.name,
                "reported_message_link": message.jump_url,
                "abuse_type": "Offensive Content",
                "reporter_name": "ModBot",
                "channel": message.channel.name,
            }

            # Insert the report into the database
            d = supabase.table('reports').insert({key: value for key, value in data.items()}).execute().data
            report_id = d[0]['id']

            # Include the id of the report in the db
            data['report_id'] = report_id

            # Check how many reports this user has made and include that for moderator reference
            user_reports = supabase.table('reports').select('reporter_id').eq('reporter_id', data["reporter_id"]).execute().data
            data['report_count'] = len(user_reports)

            # Check how many times the author has been warned
            # Query the database for authorId and decision = warning
            warnings = supabase.table('reports').select('authorId').eq('authorId', data["authorId"]).eq('decision', 'Your report has been reviewed. The message has been deleted and the user has been warned.').execute().data
            data["warning_count"] = len(warnings)
            await mod_channel.send(f"{data}")

    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel,
        insert your code here! This will primarily be used in Milestone 3.
        '''
        # Message content is the text of the message
        # Message.attachments is a list of Attachment objects, each with id, filename and url

        if message.content != "" and len(message.attachments) == 0:
            # TODO: figure out how to handle text only cases
            return message.content
        elif len(message.attachments) > 0:
            total_abuse = False
            for attachment in message.attachments:
                # TODO: better checks for image files
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                    # Evaluate if the image is animal abuse
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "This is an image from Tom and Jerry. We define 'proxy animal abuse' as any violent behavior (or behavior that would cause stress) towards any animals present in the image. Does this image contain 'proxy animal abuse'? Only answer with Yes or No."},
                                {
                                "type": "image_url",
                                "image_url": {
                                    "url": attachment.url,
                                },
                                },
                            ],
                            }
                        ],
                        max_tokens=300,
                        )

                    if response.choices[0].message.content.startswith("Yes"):
                        total_abuse = True
            if total_abuse:
                return "This message contains animal abuse."
            else:
                return "This message does not contain animal abuse."

        return message.content


    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been
        evaluated, insert your code here for formatting the string to be
        shown in the mod channel.
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)
