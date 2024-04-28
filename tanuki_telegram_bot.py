
import json, os
from time import sleep
from typing import Final
from random import random, randrange
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

import requests

# can't activate virtual env?
# Set-ExecutionPolicy Unrestricted -Scope Process


load_dotenv()

with open("tanuki_prompt.json", "r") as file:
    PROMPT_DATA = json.load(file)

with open("whitelist.txt", 'r') as whitelist:
    WHITELIST = whitelist.read()

URL: Final = 'http://localhost:5001/api/v1/generate/'
TOKEN: Final = os.environ.get("API-KEY")
CONTEXT_IDX: Final = len(PROMPT_DATA["context"])

BOT_USERNAME: Final = 'Tanuki_Bot'

def switch_context(context: ContextTypes.DEFAULT_TYPE):
    rando = randrange(0, CONTEXT_IDX)
    context.user_data["title"] = PROMPT_DATA["context"][str(rando)]["title"]
    context.user_data["convo"] = [PROMPT_DATA["context"][str(rando)]["context_primer"]]

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    switch_context(context)
    await update.message.reply_text(f""" <<< Refresh >>>\n context: {context.user_data["title"]} """)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(""" Here are a list of commands:
                                    
                                        /pic    - request a picture 
                                        /restart    - change conversation context """)

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("What would you like to do now?")

async def send_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("tanuki_profile.jpg", "rb") as my_pic:
        await update.message.reply_photo(my_pic, caption="How do I look? >_>")

def handle_response(text: str, context: ContextTypes.DEFAULT_TYPE):

    #edit user text message input
    processed: str = text.lower()

    #check condition of and maintain recent user input:
    if not context.user_data.get("convo"):
        switch_context(context)

    if len(context.user_data["convo"]) > 10: 
        print("____ clipping prompt ____", len(context.user_data["convo"]) )
        clipped_prompt = [context.user_data["convo"][0]]
        context.user_data["convo"] = clipped_prompt

    #update conversation, send to ai for prediction
    context.user_data['convo'].append(processed)
    marginal_prompt = "".join(context.user_data['convo']) + "\nTanuki: "
    
    PROMPT_DATA["prompt_payload"]["prompt"] = marginal_prompt
    print(" USER DATA --> : " + marginal_prompt)

    #post to kobold API
    response = requests.post(URL, json=PROMPT_DATA["prompt_payload"]).json()
    ans = response.get("results")[0].get("text")

    #update conversation with ai response/prediction
    context.user_data['convo'].append("\nTanuki: "+ans)

    reply = ans.replace("\nTanuki:","").replace("\nYou:","").replace("<|im_end|>","")
    reply = "!!" if ans == "" else reply
    
    return reply

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    chat_id: str = str(update.message.chat_id)
    username: str = update.message.chat.username

    if username not in WHITELIST:
        print(f'User {username} ({chat_id}) tried issuing a command but was not allowed.')

    else:
        print(f"User ({update.message.chat.id}) in {message_type}: '{text}'")

        if message_type == "group":
            if BOT_USERNAME in text:
                new_text: str = text.replace(BOT_USERNAME, "").strip()
                response: str = handle_response(new_text)
            else:
                return

        else:
            response: str = handle_response(text, context)

        print("--->", response)

        await context.bot.sendChatAction(chat_id=update.effective_message.chat_id, action = 'typing')

        sleep(random() * 2 + 3.)
        await update.message.reply_text(response)
 
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    print("starting bot . . .")
        
    app = Application.builder().token(TOKEN).build()

    #commands
    app.add_handler(CommandHandler('restart', restart_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))
    app.add_handler(CommandHandler('pic', send_pic))

    #messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #errors
    app.add_error_handler(error)

    print("polling . . .")
    app.run_polling(poll_interval=3)