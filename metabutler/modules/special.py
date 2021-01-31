import asyncio
import base64
import datetime
import gc
import glob
import html
import inspect
import io
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import textwrap
import time
import traceback
import urllib
from contextlib import redirect_stdout
from typing import List, Optional

import PIL
import psutil
import pyowm
import requests
import urbandict
import wikipedia
from bs4 import BeautifulSoup
from metabutler import (LOGGER, OWNER_ID, SUDO_USERS, SUPPORT_USERS,
                        WHITELIST_USERS, dispatcher)
from metabutler.__main__ import STATS, USER_INFO
from metabutler.modules.disable import DisableAbleCommandHandler
from metabutler.modules.helper_funcs.alternate import send_message
from metabutler.modules.helper_funcs.extraction import extract_user
from metabutler.modules.helper_funcs.filters import CustomFilters
from pyowm import exceptions, timeutils
from telegram import (Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup,
                      Message, MessageEntity, ParseMode, Update)
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, Filters, MessageHandler, run_async
from telegram.utils.helpers import (escape_markdown, mention_html,
                                    mention_markdown)
from telegraph import Telegraph, upload_file

BASE_URL = 'https://del.dog'
namespaces = {}


def namespace_of(chat, update, context):
    if chat not in namespaces:
        namespaces[chat] = {
            '__builtins__': globals()['__builtins__'],
            'context.bot': context.bot,
            'effective_message': update.effective_message,
            'effective_user': update.effective_user,
            'effective_chat': update.effective_chat,
            'update': update
        }

    return namespaces[chat]


def log_input(update):
    user = update.effective_user.id
    chat = update.effective_chat.id
    LOGGER.info(f"IN: {update.effective_message.text} (user={user}, chat={chat})")


def send(msg, update, context):
    LOGGER.info(f"OUT: '{msg}'")
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"`{msg}`", parse_mode=ParseMode.MARKDOWN)


#@run_async
#def evaluate(update, context):
#    send(do(eval, update, context), update, context)


#@run_async
#def execute(update, context):
#    send(do(exec, update, context), update, context)


#def cleanup_code(code):
#    if code.startswith('```') and code.endswith('```'):
#        return '\n'.join(code.split('\n')[1:-1])
#    return code.strip('` \n')


#def do(func, update, context):
#    log_input(update)
#    content = update.message.text.split(' ', 1)[-1]
#    body = cleanup_code(content)
#    env = namespace_of(update.message.chat_id, update, context)

#    os.chdir(os.getcwd())
#    with open(os.path.join(os.getcwd(), 'metabutler/modules/helper_funcs/temp.txt'), 'w') as temp:
#        temp.write(body)

#    stdout = io.StringIO()

#    to_compile = f'def func():\n{textwrap.indent(body, "  ")}'

#    try:
#        exec(to_compile, env)
#    except Exception as e:
#        return f'{e.__class__.__name__}: {e}'

#    func = env['func']

#    try:
#        with redirect_stdout(stdout):
#            func_return = func()
#    except Exception as e:
#        value = stdout.getvalue()
#        return f'{value}{traceback.format_exc()}'
#    else:
#        value = stdout.getvalue()
#        result = None
#        if func_return is None:
#            if value:
#                result = f'{value}'
#            else:
#                try:
#                    result = f'{repr(eval(body, env))}'
#                except:
#                    pass
#        else:
#            result = f'{value}{func_return}'
#        if result:
#            if len(str(result)) > 5000:
#                result = 'Output is too long'
#            return result


#@run_async
#def clear(update, context):
#    log_input(update)
#    global namespaces
#    if update.message.chat_id in namespaces:
#        del namespaces[update.message.chat_id]
#    send("Cleared locals.", update, context)

@run_async
def post_telegraph(update, context):
    args = context.args
    short_name = "Created By @MetaButler"
    msg = update.effective_message # type: Optional[Message]
    telegraph = Telegraph()
    r = telegraph.create_account(short_name=short_name)
    auth_url = r["auth_url"]
    LOGGER.info(auth_url)
    title_of_page = " ".join(args)
    page_content = msg.reply_to_message.text
    page_content = page_content.replace("\n", "<br>")
    response = telegraph.create_page(
        title_of_page,
        html_content=page_content
    )
    send_message(update.effective_message, "https://telegra.ph/{}".format(response["path"]))


@run_async
def getlink(update, context):
	args = context.args
	if args:
		chat_id = int(args[0])
	else:
		send_message(update.effective_message, "You don't seem to be referring to chat")
	chat = context.bot.getChat(chat_id)
	bot_member = chat.get_member(context.bot.id)
	if bot_member.can_invite_users:
		titlechat = context.bot.get_chat(chat_id).title
		invitelink = context.bot.get_chat(chat_id).invite_link
		send_message(update.effective_message, "Successfully retrieve the invite link in the group {}. \nInvite link : {}".format(titlechat, invitelink))
	else:
		send_message(update.effective_message, "I don't have access to the invitation link!")
	
@run_async
def leavechat(update, context):
	args = context.args
	if args:
		chat_id = int(args[0])
	else:
		send_message(update.effective_message, "You don't seem to be referring to chat")
	try:
		chat = context.bot.getChat(chat_id)
		titlechat = context.bot.get_chat(chat_id).title
		context.bot.sendMessage(chat_id, "Goodbye everyone")
		context.bot.leaveChat(chat_id)
		send_message(update.effective_message, "I have left the group {}").format(titlechat)

	except BadRequest as excp:
		if excp.message == "Chat not found":
			send_message(update.effective_message, "Looks like I have been out or kicked in the group")
		else:
			return


@run_async
def wiki(update, context):
    args = context.args
    try:
        reply = " ".join(args)
        summary = f"{wikipedia.summary(reply, sentences=3)}"
        keyboard = [[
            InlineKeyboardButton(
                text="click here for read more",
                url=f"{wikipedia.page(reply).url}")
        ]]
        send_message(update.effective_message, summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    except wikipedia.PageError as e:
        send_message(update.effective_message, "Error: {}".format(e))
    except BadRequest as et:
        send_message(update.effective_message, "Error: {}".format(et))
    except wikipedia.exceptions.DisambiguationError as eet:
        send_message(update.effective_message, 
                "Error\n There are too many query! Express it more!\nPossible query result:\n{}"
                .format(eet))

@run_async
def urbandictionary(update, context):
    message = update.effective_message
    text = message.text[len('/ud '):]
    results = requests.get(f'http://api.urbandictionary.com/v0/define?term={text}').json()
    try:
        reply_text = f'*{text}*\n\n{results["list"][0]["definition"]}\n\n_{results["list"][0]["example"]}_'
    except:
        reply_text = "No results found."
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN)


@run_async
def paste(update, context):
    message = update.effective_message
    args = context.args

    if message.reply_to_message:
        data = message.reply_to_message.text
    elif len(args) >= 1:
        data = message.text.split(None, 1)[1]
    else:
        send_message(update.effective_message, "What am I supposed to do with this?!")
        return

    r = requests.post(f'{BASE_URL}/documents', data=data.encode('UTF-8'))

    if r.status_code == 404:
        send_message(update.effective_message, 'Failed to reach dogbin')
        r.raise_for_status()

    res = r.json()

    if r.status_code != 200:
        send_message(update.effective_message, res['message'])
        r.raise_for_status()

    key = res['key']
    if res['isUrl']:
        reply = f'Shortened URL: {BASE_URL}/{key}\nYou can view stats, etc. [here]({BASE_URL}/v/{key})'
    else:
        reply = f'{BASE_URL}/{key}'
    send_message(update.effective_message, reply, parse_mode=ParseMode.MARKDOWN)

@run_async
def get_paste_content(update, context):
    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        key = args[0]
    else:
        send_message(update.effective_message, "Please supply a paste key!")
        return

    format_normal = f'{BASE_URL}/'
    format_view = f'{BASE_URL}/v/'

    if key.startswith(format_view):
        key = key[len(format_view):]
    elif key.startswith(format_normal):
        key = key[len(format_normal):]

    r = requests.get(f'{BASE_URL}/raw/{key}')

    if r.status_code != 200:
        try:
            res = r.json()
            send_message(update.effective_message, res['message'])
        except Exception:
            if r.status_code == 404:
                send_message(update.effective_message, 'Failed to reach dogbin')
            else:
                send_message(update.effective_message, 'Unknown error occured')
        r.raise_for_status()

    send_message(update.effective_message, '```' + escape_markdown(r.text) + '```', parse_mode=ParseMode.MARKDOWN)

@run_async
def get_paste_stats(update, context):
    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        key = args[0]
    else:
        send_message(update.effective_message, "Please supply a paste key!")
        return

    format_normal = f'{BASE_URL}/'
    format_view = f'{BASE_URL}/v/'

    if key.startswith(format_view):
        key = key[len(format_view):]
    elif key.startswith(format_normal):
        key = key[len(format_normal):]

    r = requests.get(f'{BASE_URL}/documents/{key}')

    if r.status_code != 200:
        try:
            res = r.json()
            send_message(update.effective_message, res['message'])
        except Exception:
            if r.status_code == 404:
                send_message(update.effective_message, 'Failed to reach dogbin')
            else:
                send_message(update.effective_message, 'Unknown error occured')
        r.raise_for_status()

    document = r.json()['document']
    key = document['_id']
    views = document['viewCount']
    reply = f'Stats for **[/{key}]({BASE_URL}/{key})**:\nViews: `{views}`'
    send_message(update.effective_message, reply, parse_mode=ParseMode.MARKDOWN)

@run_async
def slist(update, context):
    message = update.effective_message
    text1 = "My sudo users are:"
    # text2 = "My support users are:"
    for user_id in SUDO_USERS:
        try:
            user = context.bot.get_chat(user_id)
            name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
            if user.username:
                name = escape_markdown("@" + user.username)
            text1 += "\n • {}".format(name)
        except BadRequest as excp:
            if excp.message == 'Chat not found':
                text1 += "\n • ({}) • not found".format(user_id)
    # for user_id in SUPPORT_USERS:
    #     try:
    #         user = bot.get_chat(user_id)
    #         name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
    #         if user.username:
    #             name = escape_markdown("@" + user.username)
    #         text2 += "\n - `{}`".format(name)
    #     except BadRequest as excp:
    #         if excp.message == 'Chat not found':
    #             text2 += "\n - ({}) - not found".format(user_id)
    send_message(update.effective_message, text1 + "\n", parse_mode=ParseMode.MARKDOWN)

#@run_async
#def log(update, context):
#	message = update.effective_message
#	eventdict = message.to_dict()
#	jsondump = json.dumps(eventdict, indent=4)
#	send_message(update.effective_message, jsondump)

@run_async
def github(update, context):
    message = update.effective_message
    if len(message.text.split()) < 2:
        reply_text = "You need to provide an username to query for duh!"
        message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        username = update.effective_message.text.split()[1]
        print(username)
        request_url = f'https://api.github.com/users/{username}'
        response_url = requests.get(request_url).json()
        reply_text = None
        photo_url = None
        if response_url.get('login'):
            if response_url.get('avatar_url'):
                photo_url = response_url.get('avatar_url')
            if response_url.get('html_url'):
                reply_text = f"*Username:* [{username}]({response_url.get('html_url')})\n"
            if response_url.get('type'):
                reply_text += f"*Account Type:* `{response_url.get('type')}`\n"
            if response_url.get('name'):
                reply_text += f"*Name:* `{response_url.get('acc_name')}`\n"
            if response_url.get('blog'):
                reply_text += f"*Blog:* [Click Here]({response_url.get('blog')})\n"
            if response_url.get('location'):
                reply_text += f"*Location:* `{response_url.get('location')}`\n"
            if response_url.get('bio'):
                reply_text += f"*Bio:* `{response_url.get('bio')}`\n"
            if response_url.get('public_repos'):
                reply_text += f"*Public Repositories:* `{response_url.get('public_repos')}`\n"
            if response_url.get('public_gists'):
                reply_text += f"*Public Gists:* `{response_url.get('public_gists')}`\n"
            if response_url.get('followers'):
                reply_text += f"*Followers:* `{response_url.get('followers')}`\n"
            if response_url.get('following'):
                reply_text += f"*Following:* `{response_url.get('following')}`\n"
            if response_url.get('created_at'):
                created_date = datetime.strptime(response_url.get('created_at'), '%Y-%m-%dT%H:%M:%SZ')
                reply_text += f"*Account Created At:* `{created_date}`\n"
            if response_url.get('updated_at'):
                updated_date = datetime.strptime(response_url.get('updated_at'), '%Y-%m-%dT%H:%M:%SZ')
                reply_text += f"*Account Updated At:* `{updated_date}`\n"
            
            if photo_url:
                message.reply_photo(photo_url, caption=reply_text, parse_mode=ParseMode.MARKDOWN)
            else:
                message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            reply_text = "GitHub user not found."
            message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

__help__ = """
 - /wiki <text>: search for text written from the wikipedia source
 - /ud <text>: search from urban dictionary
 - /paste: Create a paste or a shortened url using [dogbin](https://del.dog)
 - /getpaste: Get the content of a paste or shortened url from [dogbin](https://del.dog)
 - /pastestats: Get stats of a paste or shortened url from [dogbin](https://del.dog)
 - /tele <text> - as reply to a long message
 - /git <username> - Get GitHub details of the username
"""

__mod_name__ = "special"

GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler(["leavechat", "leavegroup", "leave"], leavechat, pass_args=True, filters=Filters.user(OWNER_ID))
WIKIPEDIA_HANDLER = DisableAbleCommandHandler("wiki", wiki, pass_args=True)
UD_HANDLER = DisableAbleCommandHandler("ud", urbandictionary)
PASTE_HANDLER = DisableAbleCommandHandler("paste", paste, pass_args=True)
GET_PASTE_HANDLER = DisableAbleCommandHandler("getpaste", get_paste_content, pass_args=True)
PASTE_STATS_HANDLER = DisableAbleCommandHandler("pastestats", get_paste_stats, pass_args=True)
#LOG_HANDLER = DisableAbleCommandHandler("log", log, filters=Filters.user(OWNER_ID))
SLIST_HANDLER = CommandHandler("slist", slist, filters=Filters.user(OWNER_ID))
GITHUB_HANDLER = DisableAbleCommandHandler("git", github, admin_ok=True, pass_args=True)
#eval_handler = CommandHandler('eval', evaluate, filters=Filters.user(OWNER_ID))
#exec_handler = CommandHandler('py', execute, filters=Filters.user(OWNER_ID))
#clear_handler = CommandHandler('clearlocals', clear, filters=Filters.user(OWNER_ID))
dispatcher.add_handler(DisableAbleCommandHandler("tele", post_telegraph, pass_args=True))

dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
dispatcher.add_handler(WIKIPEDIA_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(SLIST_HANDLER)
dispatcher.add_handler(PASTE_HANDLER)
dispatcher.add_handler(GET_PASTE_HANDLER)
dispatcher.add_handler(PASTE_STATS_HANDLER)
dispatcher.add_handler(GITHUB_HANDLER)
#dispatcher.add_handler(LOG_HANDLER)
#dispatcher.add_handler(eval_handler)
#dispatcher.add_handler(exec_handler)
#dispatcher.add_handler(clear_handler)
