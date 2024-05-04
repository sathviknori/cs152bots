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
    ADDITIONAL_INFO = auto()
    ANIMAL_ABUSE = auto()
    TARGET = auto()
    USER = auto()
    FINAL_ACTIONS = auto()

offense = {
    "1": "Dehumanizing/derogatory remarks",
    "2": "Sexual Content",
    "3": "Violence",
    "4": "Hate Speech",
    "5": "Animal abuse/torture"
}

harrassment = {
    "1": "sexual harrasment",
    "2": "targeted harrasment against protected class",
    "3": "repeated bullying"
}

danger = {
    "1": "threats to safety",
    "2": "Encouragement of self-harm or suicidal ideation"
}

animal_abuse = {
    "1": "Poor Living Conditions",
    "2": "Physical Torture/Violence",
    "3": "Threaten to Torture/Commit Violence"
}

suggested_actions = {
    "1": "Delete Message",
    "2": "Warn User",
    "3": "Ban User"
}

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.data = {}
        self.mod_channel = None
        self.channel = None
    
    async def handle_message(self, message, mod_channels):
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
            self.data['reported_message_link'] = message.content
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            self.channel = channel
            self.mod_channel = mod_channels.get(guild.id)
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
                self.data['abuse_type'] = "Spam/Fraud"
                self.state = State.ADDITIONAL_INFO
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            if re.search('2', message.content):
                self.data['abuse_type'] = "Offensive Content"
                self.state = State.OFFENSIVE
                reply ="Please select type of offensive content: \n"
                reply += '(1) Dehumanizing/derogatory remarks \n (2)  Sexual Content \n (3) Violence \n (4) Hate Speech \n (5) Animal abuse/torture'
                return [reply]
            if re.search('3', message.content):
                self.data['abuse_type'] = "Bullying/Harassment"
                self.state = State.HARRASMENT
                reply ="Please select type of harrasment: \n"
                reply += '(1) sexual harrasment \n (2) targeted harrasment against protected class \n (3) repeated bullying'
                return [reply]
            if re.search('4', message.content):
                self.data['abuse_type'] = "Violent/Dangerous"
                self.state = State.DANGER
                return ["Please specify what type of danger/violence you are reporting: \n(1) threats to safety\n(2) Encouragement of self-harm or suicideal ideation"]
        
        if self.state == State.ADDITIONAL_INFO:
            self.state = State.FINAL_ACTIONS
            if message.content != "no":
                self.data["additional_info"] = message.content
            return ["If you have any suggestions on what action should be taken, please give your input: \n (1) Delete Message \n (2) Warn User \n (3) Ban User"]
        
        if self.state == State.OFFENSIVE:
            if not re.search('5', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = offense.get(message.content, message.content)
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            else:
                self.state = State.ANIMAL_ABUSE
                return ["Please specify what type of animal abuse you are reporting: \n(1) Poor Living Conditions\n (2) Physical Torture/Violence\n (3) Threaten to Torture/Commit Violence"]

        if self.state == State.ANIMAL_ABUSE:
            self.state = State.ADDITIONAL_INFO
            self.data['animal_abuse_type'] = animal_abuse.get(message.content, message.content)
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]

        if self.state == State.HARRASMENT:
            self.state = State.TARGET
            self.data['harrassment_type'] = harrassment.get(message.content, message.content)
            return ["Is this abuse against you or someone else: \n (1) Me \n (2) Someone else"]
        
        if self.state == State.TARGET:
            if re.search('1', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['target'] = message.author
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            else:
                self.state = State.USER
                return ["Please enter the username of who is being targeted"]
        
        if self.state == State.USER:
            self.state = State.ADDITIONAL_INFO
            self.data['target'] = message.content
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]


        if self.state == State.DANGER:
            self.data['danger_type'] = danger.get(message.content, message.content)
            self.state = State.ADDITIONAL_INFO
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
        
        if self.state == State.FINAL_ACTIONS:
            self.state = State.REPORT_COMPLETE
            self.data['action'] = suggested_actions.get(message.content, message.content)
            print('Report Data:', self.data)
            self.data['authorId'] = message.author.id
            self.data['authorUserName'] = message.author.name
            self.data['channel'] = self.channel.name
            await self.mod_channel.send(f"{self.data}")
            return ["Your report has been submitted. Thank you for your help!"]

        return ["error try again"]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

