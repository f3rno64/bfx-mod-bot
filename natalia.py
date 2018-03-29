#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A Simple way to send a message to telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram import MessageEntity, TelegramObject, ChatAction
from pprint import pprint
from functools import wraps
from future.builtins import bytes
from pymongo import MongoClient
from pathlib import Path
import numpy as np
import argparse
import logging
import telegram
import sys
import json
import random
import datetime
from dateutil.relativedelta import relativedelta
import re
import os
import sys
import yaml
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from PIL import Image

# For plotting messages / price charts
import pandas as pd

import requests

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch
from matplotlib.finance import candlestick_ohlc

import talib as ta

from urllib.parse import quote_plus

PATH = os.path.dirname(os.path.abspath(__file__))

"""
# Configure Logging
"""
FORMAT = '%(asctime)s -- %(levelname)s -- %(module)s %(lineno)d -- %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger('root')
logger.info("Running "+sys.argv[0])

"""
#	Load the config file
#	Set the Botname / Token
"""
config_file = "%s/config.yaml" % (PATH)
my_file     = Path(config_file)

if my_file.is_file():
	with open(config_file) as fp:
	    config = yaml.load(fp)
else:
	pprint('config.yaml file does not exists. Please make from config.sample.yaml file')
	sys.exit()

"""
# Mongodb
"""
client = MongoClient(
	username=config['MDB_USER'],
	password=config['MDB_PW'],
	host=("mongodb://%s:%d/%s?authSource=%s" % (
		config['MDB_HOST'], config['MDB_PORT'], config['MDB_DB'], config['MDB_DB']
	))
)

db = client.bfx_mod_bot

BOTNAME                     = config['NATALIA_BOT_USERNAME']
TELEGRAM_BOT_TOKEN          = config['NATALIA_BOT_TOKEN']
FORWARD_PRIVATE_MESSAGES_TO = config['BOT_OWNER_ID']
ADMINS                      = config['ADMINS']

AFFILIATE_LINK_DETECTOR = r""+config['AFFILIATE_LINK_DETECTOR']

MESSAGES = {}
MESSAGES['welcome']         = config['MESSAGES']['welcome']
MESSAGES['goodbye']         = config['MESSAGES']['goodbye']
MESSAGES['pmme']            = config['MESSAGES']['pmme']
MESSAGES['start']           = config['MESSAGES']['start']
MESSAGES['admin_start']     = config['MESSAGES']['admin_start']
MESSAGES['rules']           = config['MESSAGES']['rules']
MESSAGES['affiliate_link_warning']           = config['MESSAGES']['affiliate_link_warning']
MESSAGES['new_user_mute_notice'] = config['MESSAGES']['new_user_mute_notice']
MESSAGES['affiliate_link_mute_notice'] = config['MESSAGES']['affiliate_link_mute_notice']

ADMINS_JSON                 = config['MESSAGES']['admins_json']
ADMIN_ID = config['ADMIN_ID']

MUTE_PERIOD_H = config['MUTE_PERIOD_HOURS']

# Rooms
BITFINEX_CHAT_ID = config['BITFINEX_CHAT_ID']

ROOM_ID_TO_NAME = {
	BITFINEX_CHAT_ID: config['BITFINEX_CHAT_NAME'],
}

# Rooms where chat/gifs/etc is logged for stats etc
LOG_ROOMS = [BITFINEX_CHAT_ID]

# Storing last 'welcome' message ids
PRIOR_WELCOME_MESSAGE_ID = {
	BITFINEX_CHAT_ID: 0
}

# Storing last 'removal' of uncompress images, message ids
LASTUNCOMPRESSED_IMAGES = {
	BITFINEX_CHAT_ID: 0
}

#################################
# Begin bot..
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Bot error handler
def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

# Restrict bot functions to admins
def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

#################################
#			UTILS

# Resolve message data to a readable name
def get_name(update):
		try:
				name = update.message.from_user.first_name
		except (NameError, AttributeError):
				try:
						name = update.message.from_user.username
				except (NameError, AttributeError):
						logger.info("No username or first name.. wtf")
						return	""
		return name

#################################
#		BEGIN BOT COMMANDS

# Returns the user their user id
def getid(bot, update):
	pprint(update.message.chat.__dict__, indent=4)
	update.message.reply_text(str(update.message.chat.title)+" :: "+str(update.message.chat.id))

# Welcome message
def start(bot, update):
	user_id = update.message.from_user.id
	chat_id = update.message.chat.id
	message_id = update.message.message_id
	user_id = update.message.from_user.id
	name = get_name(update)

	logger.info("/start - "+name)
	logger.info(chat_id)

	pprint(update.message.chat.type)

	if (update.message.chat.type == 'group') or (update.message.chat.type == 'supergroup'):
		msg = random.choice(MESSAGES['pmme']) % (name)
		bot.sendMessage(chat_id=chat_id,text=msg,reply_to_message_id=message_id, parse_mode="Markdown",disable_web_page_preview=1)
	else:
		msg = MESSAGES['rules']

		timestamp = datetime.datetime.utcnow()
		info = { 'user_id': user_id, 'request': 'start', 'timestamp': timestamp }
		db.pm_requests.insert(info)

		msg = bot.sendMessage(chat_id=chat_id, text=(MESSAGES['start'] % name),parse_mode="Markdown",disable_web_page_preview=1)

		if user_id in ADMINS:
			msg = bot.sendMessage(chat_id=chat_id, text=(MESSAGES['admin_start'] % name),parse_mode="Markdown",disable_web_page_preview=1)

def rules(bot, update):
	user_id = update.message.from_user.id
	chat_id = update.message.chat.id
	message_id = update.message.message_id
	name = get_name(update)

	if (update.message.chat.type == 'group') or (update.message.chat.type == 'supergroup'):
		msg = random.choice(MESSAGES['pmme']) % (name)
		bot.sendMessage(chat_id=chat_id,text=msg,reply_to_message_id=message_id, parse_mode="Markdown",disable_web_page_preview=1)
	else:
		msg = MESSAGES['rules']

		timestamp = datetime.datetime.utcnow()
		info = { 'user_id': user_id, 'request': 'rules', 'timestamp': timestamp }
		db.pm_requests.insert(info)

		bot.sendMessage(chat_id=chat_id,text=msg,parse_mode="Markdown",disable_web_page_preview=1)

def admins(bot, update):

	user_id = update.message.from_user.id
	chat_id = update.message.chat.id
	message_id = update.message.message_id
	name = get_name(update)

	if (update.message.chat.type == 'group') or (update.message.chat.type == 'supergroup'):
		msg = random.choice(MESSAGES['pmme']) % (name)
		bot.sendMessage(chat_id=chat_id,text=msg,reply_to_message_id=message_id, parse_mode="Markdown",disable_web_page_preview=1)
	else:
		msg = "*Bitfinex TG Admins*\n\n"
		keys = list(ADMINS_JSON.keys())
		random.shuffle(keys)
		for k in keys:
			msg += ""+k+"\n"
		msg += "\n/start - to go back to home"

		timestamp = datetime.datetime.utcnow()
		info = { 'user_id': user_id, 'request': 'admins', 'timestamp': timestamp }
		db.pm_requests.insert(info)

		bot.sendMessage(chat_id=chat_id,text=msg,parse_mode="Markdown",disable_web_page_preview=1)

####################################################
# ADMIN FUNCTIONS
@restricted
def commandstats(bot, update):
	chat_id = update.message.chat_id
	start = datetime.datetime.today().replace(day=1,hour=0,minute=0,second=0)
	# start = start - relativedelta(days=30)

	pipe = [
		{ "$match": { 'timestamp': {'$gt': start } } },
		{ "$group": {
			"_id": {
				"year" : { "$year" : "$timestamp" },
				"month" : { "$month" : "$timestamp" },
				"day" : { "$dayOfMonth" : "$timestamp" },
				"request": "$request"
			},
			"total": { "$sum": 1 }
			}
		},
		{ "$sort": { "total": -1  } },
		# { "$limit": 3 }
	]
	res = list(db.pm_requests.aggregate(pipe))

	output = {}
	totals = {}

	for r in res:

		key = r['_id']['day']
		if not(key in output):
			output[key] = {}

		request = r['_id']['request']
		if not(request in output[key]):
			output[key][r['_id']['request']] = 0

		if not(request in totals):
			totals[request] = 0

		output[key][r['_id']['request']] += r['total']
		totals[request] += r['total']


	reply = "*Natalia requests since the start of the month...*\n"
	for day in sorted(output.keys()):
		reply += "--------------------\n"
		reply += "*"+str(day)+"*\n"

		for request, count in output[day].items():
			reply += request+" - "+str(count)+"\n"


	reply += "--------------------\n"
	reply += "*Totals*\n"
	for request in totals:
		reply += request+" - "+str(totals[request])+"\n"


	bot.sendMessage(chat_id=chat_id, text=reply, parse_mode="Markdown" )

#################################
#		BOT EVENT HANDLING
def new_chat_member(bot, update):
	""" Welcomes new chat member """

	logger.info(update)

	member = update.message.new_chat_members[0]
	user_id = member.id
	message_id = update.message.message_id
	chat_id = update.message.chat.id
	name = member.first_name

	logger.info(chat_id)

	if (chat_id != BITFINEX_CHAT_ID):
		return

	# Check user has a profile pic..
	# TODO: Extract
	timestamp = datetime.datetime.utcnow()
	info = { 'user_id': user_id, 'chat_id': chat_id, 'timestamp': timestamp }
	db.room_joins.insert(info)

	profile_pics = bot.getUserProfilePhotos(user_id=user_id)

	if profile_pics.total_count == 0:
		logger.info("user %d tried to join without a profile picture" % (user_id))
		bot.sendMessage(
			chat_id=chat_id,
			reply_to_message_id=message_id,
			text='You need a profile picture to join this channel'
		)

		return

	try:
		if PRIOR_WELCOME_MESSAGE_ID[chat_id] > 0:
			bot.delete_message(chat_id=chat_id, message_id=PRIOR_WELCOME_MESSAGE_ID[chat_id])
	except:
		pass

	logger.info("welcoming new user - %s" % (name))

	message = bot.sendMessage(
		chat_id=chat_id,
		text=MESSAGES['welcome'] % (name),
		parse_mode='Markdown'
	)

	PRIOR_WELCOME_MESSAGE_ID[chat_id] = int(message.message_id)

	db.users.insert({
		'user_id': user_id,
		'timestamp': timestamp
	})

	bot.restrict_chat_member(
		chat_id,
		user_id,
		until_date=(datetime.datetime.now() + relativedelta(hours=MUTE_PERIOD_H)),
		can_send_messages=False,
		can_send_media_messages=False,
		can_send_other_messages=False,
		can_add_web_page_previews=False
	)

	bot.sendMessage(
		chat_id=user_id,
		text=MESSAGES['new_user_mute_notice'],
		parse_mode="Markdown",
		disable_web_page_preview=1
	)

# Disabled
def left_chat_member(bot, update):
	logger.info(update)

	name = get_name(update)
	message = update.message
	logger.info(message.left_chat_member.first_name+' left chat '+message.chat.title)
	name = get_name(update)

	bot.sendMessage(
		chat_id=update.message.chat.id,
		reply_to_message_id=message.message_id,
		text=random.choice(MESSAGES['goodbye']),
		parse_mode="Markdown",
		disable_web_page_preview=1
	)

# Just log/handle a normal message
def log_message_private(bot, update):
	username = update.message.from_user.username
	user_id = update.message.from_user.id
	message_id = update.message.message_id
	chat_id = update.message.chat.id
	name = get_name(update)

	logger.info("Private Log Message: "+name+" said: "+update.message.text)

	msg = bot.forwardMessage(chat_id=FORWARD_PRIVATE_MESSAGES_TO, from_chat_id=chat_id, message_id=message_id)

	msg = bot.sendMessage(chat_id=chat_id, text=(MESSAGES['start'] % name),parse_mode="Markdown",disable_web_page_preview=1)


# Just log/handle a normal message
def echo(bot, update):
	username = update.message.from_user.username
	user_id = update.message.from_user.id
	message_id = update.message.message_id
	chat_id = update.message.chat.id

	if username == None:
		return

	message = username+': '+update.message.text
	pprint(str(chat_id)+" - "+str(message))

	name = get_name(update)
	timestamp = datetime.datetime.utcnow()

	info = { 'user_id': user_id, 'chat_id': chat_id, 'message_id':message_id, 'message': message, 'timestamp': timestamp }
	db.natalia_textmessages.insert(info)

	info = { 'user_id': user_id, 'name': name, 'username': username, 'last_seen': timestamp }
	db.users.update_one( { 'user_id': user_id }, { "$set": info }, upsert=True)

def on_delete_message(bot, update):
	message_id = update.message.message_id
	chat_id = update.message.chat.id

	bot.delete_message(chat_id=chat_id, message_id=message_id)

def on_link_message(bot, update):
	user_id = update.message.from_user.id
	message_id = update.message.message_id
	chat_id = update.message.chat.id
	name = get_name(update)
	find_aff_link = re.findall(AFFILIATE_LINK_DETECTOR, update.message.text)

	if (len(find_aff_link) == 0):
		return

	reply = MESSAGES['affiliate_link_warning']

	bot.sendMessage(
		chat_id=ADMIN_ID,
		text=("%s posted an affiliate link" % (name)),
		parse_mode="Markdown",
		disable_web_page_preview=1
	)

	# Replace message
	bot.delete_message(chat_id=chat_id, message_id=message_id)
	bot.sendMessage(chat_id=chat_id, text=reply, parse_mode="Markdown", disable_web_page_preview=1)

	bot.sendMessage(
		chat_id=user_id,
		text=MESSAGES['affiliate_link_mute_notice'],
		parse_mode="Markdown",
		disable_web_page_preview=1
	)

	# Silence bad actor
	bot.restrict_chat_member(
		chat_id,
		user_id,
		until_date=(datetime.datetime.now() + relativedelta(hours=MUTE_PERIOD_H)),
		can_send_messages=False,
		can_send_media_messages=False,
		can_send_other_messages=False,
		can_add_web_page_previews=False
	)

#################################
# Command Handlers
updater = Updater(bot=bot,workers=10)
dp      = updater.dispatcher

# Commands
dp.add_handler(CommandHandler('id', getid))
dp.add_handler(CommandHandler('start', start))
dp.add_handler(CommandHandler('rules', rules))
dp.add_handler(CommandHandler('admins', admins))
dp.add_handler(CommandHandler('commandstats',commandstats))
dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_chat_member))
dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, left_chat_member))
dp.add_handler(MessageHandler(Filters.entity(MessageEntity.URL), on_link_message))
dp.add_handler(MessageHandler(Filters.private, log_message_private))
dp.add_handler(MessageHandler(Filters.text, echo))
dp.add_handler(MessageHandler(Filters.photo, on_delete_message))
dp.add_handler(MessageHandler(Filters.sticker, on_delete_message))
dp.add_handler(MessageHandler(Filters.video, on_delete_message))
dp.add_handler(MessageHandler(Filters.document, on_delete_message))
dp.add_error_handler(error)

#################################
# Polling
updater.start_polling()
