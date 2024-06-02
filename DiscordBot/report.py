from enum import Enum, auto
import discord
import re
from db import supabase

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    SPAM = auto()
    DANGER = auto()
    OFFENSIVE = auto()
    HARASSMENT = auto()
    ADDITIONAL_INFO = auto()
    ANIMAL_ABUSE = auto()
    TARGET = auto()
    USER = auto()
    SOMETHING_ELSE =  auto()
    PRIVATE_INFO = auto()
    MISINFORMATION = auto()
    FINAL_ACTIONS = auto()
    OTHER_DESCRIPTION = auto()
    MINOR_SEXUAL_BEHAVIOR = auto()
    SEXUAL_CONTENT_SUBTYPE = auto()


offense = {
    "1": "Dehumanizing/derogatory remarks",
    "2": "Sexual Content",
    "3": "Violence",
    "4": "Hate Speech",
    "5": "Animal abuse/torture"
}

harassment = {
    "1": "Promoting hate based on identity or vulnerability",  
    "2": "Celebrating or glorifying acts of violence", 
    "3": "Using rude, vulgar or offensive language",  
    "4": "Bullying",
    "5": "Sexual harassment"
}

danger = {
    "1": "threats to safety",
    "2": "Encouragement of self-harm or suicidal ideation"
}


misinformation = {
    "1": "Spreading fake news or harmful conspiracy theories",
    "2": "Impersonation"
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

minor_sexual_behavior_options = {
    "1": "This person is sending inappropriate sexual messages or discussing minors sexually",
    "2": "A minor is posting or sending sexual messages",
    "3": "Photos or video depicting real world child sexual abuse"
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
        self.reported_message = None
    
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
                self.reported_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            self.data['reporter_id'] = message.author.id
            self.data['reporter_name'] = message.author.name
            return ["I found this message:", "```" + self.reported_message.author.name + ": " + self.reported_message.content + "```", \
                    "Please select a category of abuse (enter number): \n (1) Spam or Fraud\n (2) Offensive Content\n (3) Bullying or Harassment\n (4) Violent/Dangerous\n (5) Harmful Misinformation\n (6) Something Else"]
        
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if re.search('1', message.content):
                self.data['abuse_type'] = "Spam or Fraud"
                self.state = State.ADDITIONAL_INFO
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            if re.search('2', message.content):
                self.data['abuse_type'] = "Offensive Content"
                self.state = State.OFFENSIVE
                reply ="Please select type of offensive content: \n"
                reply += '(1) Animal abuse or torture \n(2) Sexual Content \n(3) Violence \n(4) Hate Speech \n'
                return [reply]
            if re.search('3', message.content):
                self.data['abuse_type'] = "Bullying or Harassment"
                self.state = State.HARASSMENT  
                reply ="Please select type of harassment: \n"
                reply += '(1) Promoting hate based on identity or vulnerability \n (2) Celebrating or glorifying acts of violence \n (3) Using rude, vulgar or offensive language \n (4) Bullying \n (5) Sexual harassment'
                return [reply]
            if re.search('4', message.content):
                self.data['abuse_type'] = "Violent/Dangerous"
                self.state = State.DANGER
                return ["Please specify what type of danger/violence you are reporting: \n(1) threats to safety\n(2) Encouragement of self-harm or suicideal ideation"]

            if re.search('5', message.content):
                self.data['abuse_type'] = "Harmful Misinformation"
                self.state = State.MISINFORMATION
                reply = "Please select the type of harmful misinformation: \n"
                reply += "(1) Spreading fake news or harmful conspiracy theories\n"
                reply += "(2) Impersonation\n"
                return [reply]

            if re.search('6', message.content):
                self.data['abuse_type'] = "Something Else"
                self.state = State.SOMETHING_ELSE
                reply = "Please select one of the following options: \n"
                reply += "(1) Mentions self harm or suicide\n"
                reply += "(2) Selling drugs or other illegal goods or services\n"
                reply += "(3) Exposing private identifying information\n"
                reply += "(4) Other"
                return [reply]


        if self.state == State.ADDITIONAL_INFO:
            self.state = State.FINAL_ACTIONS
            if message.content != "no":
                self.data["additional_info"] = message.content
            return ["If you have any suggestions on what action should be taken, please give your input: \n (1) Delete Message \n (2) Warn User \n (3) Ban User"]
        
        if self.state == State.OFFENSIVE:
            if not re.search('1|2', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = offense.get(message.content, message.content)
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('2', message.content):
                self.state = State.SEXUAL_CONTENT_SUBTYPE
                reply = "Please select type of sexual content: \n"
                reply += "(1) Unwanted adult sexual images \n"
                reply += "(2) Sexual content or behavior involving a minor"
                return [reply]
            else:
                self.state = State.ANIMAL_ABUSE
                return ["Please specify what type of animal abuse you are reporting: \n(1) Poor Living Conditions\n(2) Physical Torture or Violence\n(3) Threaten to Torture or Commit Violence Towards Animals"]

        if self.state == State.ANIMAL_ABUSE:
            self.state = State.ADDITIONAL_INFO
            self.data['animal_abuse_type'] = animal_abuse.get(message.content, message.content)
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]

        if self.state == State.HARASSMENT:
            self.state = State.TARGET
            self.data['harassment_type'] = harassment.get(message.content, message.content)
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
        
        if self.state == State.MISINFORMATION:
            if re.search('1', message.content) or re.search('2', message.content):
                self.data['misinformation_type'] = misinformation.get(message.content, message.content)
                self.state = State.ADDITIONAL_INFO
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
         
        if self.state == State.SOMETHING_ELSE:
            if re.search('1', message.content):
                self.data['something_else_type'] = "Mentions self harm or suicide"
                self.state = State.ADDITIONAL_INFO
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('2', message.content):
                self.data['something_else_type'] = "Selling drugs or other illegal goods or services"
                self.state = State.ADDITIONAL_INFO
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('3', message.content):
                self.data['something_else_type'] = "Exposing private identifying information"
                self.state = State.PRIVATE_INFO
                return ["What information was posted without your consent?"]
            elif re.search('4', message.content):
                self.data['something_else_type'] = "Other"
                self.state = State.OTHER_DESCRIPTION
                return ["Please specify what you want to report."]
       
        if self.state == State.PRIVATE_INFO:
            self.state = State.ADDITIONAL_INFO
            self.data['private_info'] = message.content
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
        ...
        if self.state == State.OTHER_DESCRIPTION:
            self.state = State.ADDITIONAL_INFO
            self.data['other_description'] = message.content
            return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
        ...
        if self.state == State.FINAL_ACTIONS:
            self.state = State.REPORT_COMPLETE
            self.data['action'] = suggested_actions.get(message.content, message.content)
            print('Report Data:', self.data)
            self.data['authorId'] = self.reported_message.author.id
            self.data['authorUserName'] = self.reported_message.author.name
            self.data['channel'] = self.channel.name

            # Insert the report into the database
            d = supabase.table('reports').insert({key: value for key, value in self.data.items()}).execute().data
            report_id = d[0]['id']

            # Include the id of the report in the db
            self.data['report_id'] = report_id

            # Check how many reports this user has made and include that for moderator reference
            user_reports = supabase.table('reports').select('reporter_id').eq('reporter_id', self.data["reporter_id"]).execute().data
            self.data['report_count'] = len(user_reports)

            # Check how many times the author has been warned
            # Query the database for authorId and decision = warning
            warnings = supabase.table('reports').select('authorId').eq('authorId', self.data["authorId"]).eq('decision', 'Your report has been reviewed. The message has been deleted and the user has been warned.').execute().data
            self.data["warning_count"] = len(warnings)

            await self.mod_channel.send(f"{self.data}")
            return ["Your report has been submitted. Thank you for your help!"]

        
        if self.state == State.SEXUAL_CONTENT_SUBTYPE:
            if re.search('1', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = "Unwanted adult sexual images"
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('2', message.content):
                self.state = State.MINOR_SEXUAL_BEHAVIOR
                reply = "Please select the type of sexual content involving a minor: \n"
                reply += "(1) This person is sending inappropriate sexual messages or discussing minors sexually \n"
                reply += "(2) A minor is posting or sending sexual messages \n"
                reply += "(3) Photos or video depicting real world child sexual abuse"
                return [reply]

        if self.state == State.MINOR_SEXUAL_BEHAVIOR:
            if re.search('1', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = "This person is sending inappropriate sexual messages or discussing minors sexually"
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('2', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = "A minor is posting or sending sexual messages"
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]
            elif re.search('3', message.content):
                self.state = State.ADDITIONAL_INFO
                self.data['offensive_type'] = "Photos or video depicting real world child sexual abuse"
                return ["Is there anything other information you would like to add? If yes, please provide it now. If not, say `no`."]




        

        return ["error try again"]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

