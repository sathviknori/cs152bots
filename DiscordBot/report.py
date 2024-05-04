from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    SPAM = auto()
    DANGER = auto()
    OFFENSIVE = auto()
    HARRASMENT = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.data = {}
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select a category of abuse (enter number): \n(1) Spam/Fraud\n (2) Offensive Content\n (3) Bullying/Harassment\n (4) Violent/Dangerous"]
        
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if re.search('1', message.content):
                self.state = State.SPAM
                return ["Ok thank you for reporting Spam a moderator will take a look"]
            if re.search('2', message.content):
                self.state = State.OFFENSIVE
                reply ="Please select type of offensive content: \n"
                reply += '(1) Dehumanizing/derogatory remarks \n (2)  Sexual Content \n (3) Violence \n (4) Hate Speech \n (5) Animal abuse/torture'
                return [reply]
            if re.search('3', message.content):
                self.state = State.HARRASMENT
                reply ="Please select type of harrasment: \n"
                reply += '(1) sexual harrasment \n (2) targeted harrasment against protected class \n (3) repeated bullying'
                return [reply]
            if re.search('4', message.content):
                self.state = State.DANGER
                return ["Please specify what type of danger/violence you are reporting: \n(1) threats to safety\n(2) Encouragement of self-harm or suicideal ideation"]

        return ["error try again"]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

