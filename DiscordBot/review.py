from enum import Enum, auto
import discord
import re
import ast
from db import supabase

class State(Enum):
    REVIEW_START = auto()
    REVIEW_COMPLETE = auto()
    ABUSE_TYPE = auto()
    ANIMAL_ABUSE = auto()
    FINAL_ACTIONS = auto()
    REPORT_LINK = auto()
    SEVERITY = auto()
    ADVERSARIAL_REPORTING = auto()
    COORDINATED_HARASSMENT = auto()

final_actions_messages = {
    "1": "Your report has been reviewed. The message has been deleted and the user has been warned.",
    "2": "Your report has been reviewed. The message has been deleted and the user has been suspended.",
    "3": "Your report has been reviewed. The message has been deleted and the user has been banned.",
    "4": "Your report has been reviewed. Unfortunately, no action has been taken. We appreciate your vigilance and suggest you block the user if you feel unsafe. If you have any further concerns, please let us know."
}

class Review:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.message = None
        self.review_data = {}
        self.animal_abuse_decision = None

    async def handle_channel_message(self, message):    
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_COMPLETE
            self.message = None
            self.data = {}
            return ["Review process cancelled."]

        if self.state == State.REVIEW_START:
            reply =  "Thank you for starting the review process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please provide the message url of the report that you would like to review."
            self.state = State.REPORT_LINK
            return [reply]
    
        if self.state == State.REPORT_LINK:
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            channel = guild.get_channel(int(m.group(2)))
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this review was deleted. Please try again or say `cancel` to cancel."]

            # Parse message.content as a dictionary
            self.review_data = ast.literal_eval(message.content)
            if "animal_abuse_type" in self.review_data:
                self.state = State.ANIMAL_ABUSE
                return ["Does this message violate our policies on animal abuse?\n (1) Yes \n (2) No"]
            else:
                self.state = State.FINAL_ACTIONS
                return ["Please determine the outcome of the review:\n (1) Delete and Warn \n (2) Delete and Suspend \n (3) Delete and Ban\n (4) No Action"]

        if self.state == State.ANIMAL_ABUSE:
            if message.content in ["1", "2"]:
                if message.content == "1":
                    self.state = State.SEVERITY
                    return ["Please determine the severity of the abuse:\n (1) Mild \n (2) Moderate \n (3) Severe"]
                else:
                    self.state = State.ADVERSARIAL_REPORTING
                    return ["Is this adversarial reporting?\n(1) Yes \n(2) No"]
                    # reporting_user_id = self.review_data["authorId"]
                    # reporting_user = await self.client.fetch_user(reporting_user_id)
                    # await reporting_user.send("Your report has been reviewed. Unfortunately, no action has been taken. We appreciate your vigilance and suggest you block the user if you feel unsafe. If you have any further concerns, please let us know.")
                    # self.state = State.REVIEW_COMPLETE
                    # return ["Review complete."]
            else:
                return ["Invalid selection. Please select a valid option."]
        

        if self.state == State.ADVERSARIAL_REPORTING:
            if message.content == "1":
                reporting_user_id = self.review_data["reporter_id"]
                reporting_user = await self.client.fetch_user(reporting_user_id)
                await reporting_user.send("You have been banned due to adversarial reporting.")
                self.state = State.REVIEW_COMPLETE
                return ["The reporting user has been notified of the ban."]
            elif message.content == "2":
                reporting_user_id = self.review_data["reporter_id"]
                reporting_user = await self.client.fetch_user(reporting_user_id)
                await reporting_user.send("Your report has been reviewed. Unfortunately, no action has been taken. We appreciate your vigilance and suggest you block the user if you feel unsafe. If you have any further concerns, please let us know.")
                self.state = State.REVIEW_COMPLETE
                return ["Review complete."]
            else:
                return ["Invalid selection. Please select a valid option."]

        if self.state == State.SEVERITY:
            decision = message.content
            if decision in final_actions_messages:
                # Send a dm to the reporting user to let them know the decision
                if "reporter_id" in self.review_data:
                    reporting_user_id = self.review_data["reporter_id"]
                    reporting_user = await self.client.fetch_user(reporting_user_id)
                    await reporting_user.send(final_actions_messages[decision])

                # Send a dm to the user who posted the message to let them know the decision
                reported_user_id = self.review_data["authorId"]
                reported_user = await self.client.fetch_user(reported_user_id)
                if decision == "1":
                    await reported_user.send("Your message violates our platform policies. This is a warning.")
                elif decision == "2":
                    await reported_user.send("Your message violates our platform policies. You have been suspended.")
                elif decision == "3":
                    await reported_user.send("Your message violates our platform policies. You have been banned.")
                # print(reporting_user, reporting_user_id, decision)

                # Update the decision in the database
                data = supabase.table('reports').update({'decision': final_actions_messages[decision]}).eq('id', self.review_data["report_id"]).execute().data

                self.state = State.REVIEW_COMPLETE
                return ["Review complete."]
            else:
                return ["Invalid selection. Please select a valid option."]

        if self.state == State.FINAL_ACTIONS:
            print("TAKING FINAL ACTIONS")
            decision = message.content
            if decision in final_actions_messages:
                # Send a dm to the reporting user to let them know the decision
                if "reporter_id" in self.review_data:
                    reporting_user_id = self.review_data["reporter_id"]
                    reporting_user = await self.client.fetch_user(reporting_user_id)
                    await reporting_user.send(final_actions_messages[decision])

                # Send a dm to the user who posted the message to let them know the decision
                reported_user_id = self.review_data["authorId"]
                reported_user = await self.client.fetch_user(reported_user_id)
                if decision == "1":
                    await reported_user.send("Your message violates our platform policies. This is a warning.")
                elif decision == "2":
                    await reported_user.send("Your message violates our platform policies. You have been suspended.")
                elif decision == "3":
                    await reported_user.send("Your message violates our platform policies. You have been banned.")
                # print(reporting_user, reporting_user_id, decision)

                # Update the decision in the database
                data = supabase.table('reports').update({'decision': final_actions_messages[decision]}).eq('id', self.review_data["report_id"]).execute().data

                self.state = State.REVIEW_COMPLETE
                return ["Review complete."]
            else:
                return ["Invalid selection. Please select a valid option."]
        

    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE