# import telebot, os.path

# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

import gspread
# from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import aiohttp
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from datetime import datetime
import copy

from telebot import asyncio_helper
asyncio_helper.proxy = 'http://proxy.server:3128'

bot = AsyncTeleBot(token='7115583170:AAGjdW9aqhzRS42MegAPLDLWLxwNvNHzuvU')

# add credentials to the account
gc = gspread.service_account(filename='lore-420220.json')

# add bot
sheet = gc.open("LORE")
orders = {}

# get the scores sheet of the Spreadsheet
score_sheet = sheet.worksheet('scores')
promt_sheet = sheet.worksheet('promts')

# store user's name
global chat_to_send
chat_to_send = -1002018835612

promts_file = "promts.txt"

def extract(filename):
    data = []
    with open(filename, 'r') as file:
        for row in file.read().split('/row'):
            data.append(row.split('/cell'))
    return data


roles_text = """
・*General Secretary*: [Eugenio Animali](tg://user?id=USER_ID)
・*Professional Relations*: [Youssef Seghrouchni](tg://user?id=USER_ID)
・*Internal Relations*: [Faustine Lasmoles](tg://user?id=USER_ID)
・*Treasurer*: [Simon Charbonneau](tg://user?id=USER_ID)
・*Communication*: [Yuki Kin](tg://user?id=USER_ID)
・*Committees & Binets*: [Adelaide Ruault](tg://user?id=5208883956)
・*Integration*: [Helena Huynh](tg://user?id=USER_ID)
・*Events*: [Vladislava Zhilenko](tg://user?id=520308013)
・*Sports*: [Nadia Pelegay Royo](tg://user?id=6112468540)
・*Infrastructure*: [Mohamed El Hassani](tg://user?id=USER_ID)
"""
#---------------------------------------------------------------------------------------------
def extract_promts(filename):
    def make_dict(arrays):
        dict = {array[0] : array[1:] for array in arrays}
        for key in dict.keys():
            if key == 'inline buttons':
                # all cell are in format text: ..., call_back = ...
                # that are neccessary for the buttons
                array = []
                for button in dict[key]:
                    if button != '':
                        array.append({text.split(':')[0] : text.split(':')[1] for text in button.split('; ')})

                dict[key] = array
        return dict

    data = extract(filename)
    filtered_data = [[row[0]] + [cell for cell in row[1:] if cell != ''] for row in data]
    promts = {}
    key = None
    for row_num in range(len(filtered_data)):
        row = filtered_data[row_num]
        # if empty ->add to previous key
        if row[0] != '':
            key = row[0]
            promts[key] = []
        promts[key] += [row[1:]]
    return {key : make_dict(promts[key]) for key in promts.keys()}



def update_score(id, value):
    cell = score_sheet.find(str(id))
    cell_value = score_sheet.cell(cell.row, cell.col - 1).value
    score_sheet.update_cell(cell.row, cell.col - 1, int(cell_value) + value)

def get_items_from_table(table):
    # data = table.get_all_values()
    data = table
    items = {}
    for row_num in range(len(data)):
        if data[row_num][0] == 'Orders':
            for item_num in range(2, len(data[row_num])):
                options = data[row_num + 1][item_num]
                if options != '':
                    options = list(map(lambda item: item.strip(), options.split(',')))
                else:
                    options = []
                items[data[row_num][item_num]] = options
    return items


# menu = get_items_from_table(promt_sheet)
menu = get_items_from_table(extract(promts_file))

state = {}
orders = set()
score_requests = set()

class Order:
    def __init__(self, text, options, address, date):
        self.text = text
        self.address = address
        self.time = date
        self.options = options
        self.order = {}
        self.user = ''

class Score:
    def __init__(self, event, score, user):
        self.event = event
        self.score = score
        self.user = user

order_requests = {}
score_orders = {}

#----------------------------------------------------------------------
def get_row_by_id(id):
    data = score_sheet.get_all_values('A:D')[1:]
    for user in data:
        if len(user) >= 4 and user[3] != '' and int(user[3]) == id:
            return user

def get_username(id):
    row = get_row_by_id(id)
    if row is not None:
        return row[0], row[1]
    return None, None


async def send_promts(message, dict, markup=None):
    if dict['buttons'] != [] and markup is None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for btn in dict['buttons']:
            markup.add(types.KeyboardButton(text=btn))
    for promt in dict['promts']:
            await bot.send_message(message.chat.id, promt, reply_markup = markup)

def add_items():
    menu = get_items_from_table(extract(promts_file))
    if len(menu.items()) != 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for item in menu.keys():
                markup.add(types.KeyboardButton(text=item))
        markup.add(types.KeyboardButton(text='Go back'))
        return markup


def add_options(item):
    menu = get_items_from_table(extract(promts_file))
    if item in menu.keys():
        if menu[item] != []:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for option in menu[item]:
                    markup.add(types.KeyboardButton(text=option))
            markup.add(types.KeyboardButton(text='Go back'))
            return markup

@bot.message_handler(commands=['start'], chat_types = ['private'])
async def bot_start(message):
    state[message.chat.id] = 'greetings'
    await greetings(message)

@bot.message_handler(commands=['help'], chat_types = ['private'])
async def bot_help(message):
    promts = extract_promts(promts_file)
    tlg_id = score_sheet.find(str(message.chat.id))
    if tlg_id:
        name, lastname = score_sheet.cell(tlg_id.row, 1).value, score_sheet.cell(tlg_id.row, 2).value
        await bot.send_message(message.chat.id, f'My shawty {name.title()} {lastname.title()}!')
        state[message.chat.id] = 'describe'
        await describe(message)
    else:
        await send_promts(message, promts['Name'])
        state[message.chat.id] = 'name'

@bot.message_handler(commands=['tech'], chat_types = ['private'])
async def bot_tech(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Cancel', callback_data='cancel'))
    await bot.send_message(message.chat.id, 'How u trippin?', reply_markup=markup)
    state[message.chat.id] = 'support'


@bot.message_handler(commands=['members'], chat_types = ['private'])
async def members(message):
    await bot.send_message(message.chat.id, roles_text, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'support')
async def support(message):
    name, lastname = get_username(message.from_user.id)
    await group_bot.send_message(chat_to_send, f'{name} {lastname}: ' + message.text)
    await bot.send_message(message.chat.id, "Thanks for spillin'! We'll totally fix that up—promise, hic!")
    await bot_help(message)

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'greetings')
async def greetings(message):
    promts = extract_promts(promts_file)
    if message.text == promts['Greeting']['buttons'][0]:
        tlg_id = score_sheet.find(str(message.chat.id))
        if tlg_id:
            name, lastname = score_sheet.cell(tlg_id.row, 1).value, score_sheet.cell(tlg_id.row, 2).value
            await bot.send_message(message.chat.id, f'My shawty {name.title()} {lastname.title()}!')
            state[message.chat.id] = 'describe'
            await describe(message)
        else:
            await send_promts(message, promts['Name'])
            state[message.chat.id] = 'name'
        return
    await send_promts(message, promts['Greeting'])


# TODO: make proper handler for names
@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'name')
async def get_name(message):
    # handle only one - word answers
    if len(message.text.split(' ')) < 2:
        await bot.send_message(message.chat.id, 'Please write your full name')
    else:
        score_data = score_sheet.get_all_values()
        name, lastname = None, None
        link = None
        flag = False
        for row_num in range(1, len(score_data)):
            row = score_data[row_num]
            if all(name in (row[0] + ' ' + row[1]).split(' ') for name in message.text.lower().split(' ')):
                name, lastname = row[:2]
                flag = True
                link = row[4]
                if row[3] == '':
                    score_sheet.update_cell(row_num + 1, 4, message.chat.id)
        if not flag:
            name, lastname = tuple(message.text.lower().split(' '))
            score_sheet.append_row([name, lastname, 0, message.from_user.id, ''])
        if link is None or link == '':
            await bot.send_message(message.chat.id, f'Great! I`ll try not to forget it, {name} {lastname}')
        else:
            await bot.send_message(message.chat.id, f'My shawty, [{name.title()} {lastname.title()}]({link})!', parse_mode='Markdown')
        state[message.chat.id] = 'describe'
        await describe(message)

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'describe')
async def describe(message):
    promts = extract_promts(promts_file)
    await send_promts(message, promts['Describe'])
    state[message.chat.id] = 'idle'
    await idle(message)


@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'idle')
async def idle(message):
    promts = extract_promts(promts_file)
    # request score
    if message.text == promts['Idle']['buttons'][0]:
        if 'yes' in promts['Open'].keys():
            await bot.send_message(message.chat.id, 'What do you want to order?')
            state[message.chat.id] = 'order'
            await take_order(message)
        else:
            await bot.send_message(message.chat.id, 'Currently there is an event going on... Come right after, we will serve the best stuff')

    elif message.text == promts['Idle']['buttons'][1]:
        row = get_row_by_id(message.from_user.id)
        if row is not None:
            await bot.send_message(message.chat.id, f'Your score is {row[2]}')
            await bot.send_message(message.chat.id, 'Is there anyhting else I can help with?')
    elif message.text == promts['Idle']['buttons'][2]:
        # state[message.chat.id] = 'add score'
        await add_score(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(promts['Idle']['buttons'][0]))
        # markup.add(types.KeyboardButton(promts['Idle']['buttons'][0], web_app=types.WebAppInfo(url='https://rumata-feathers.github.io/Polytechnique-bot/')))
        markup.add(types.KeyboardButton(promts['Idle']['buttons'][1]))
        markup.add(types.KeyboardButton(promts['Idle']['buttons'][2]))

        await send_promts(message, promts['Idle'], markup=markup)


@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'order')
async def take_order(message):
    menu = get_items_from_table(extract(promts_file))
    if message.text in menu.keys():
        order_requests[message.chat.id] = Order(message.text, None, None, None)
        options = menu[message.text]

        if len(options) == 0:
            state[message.chat.id] = 'choose_address'
            markup = types.ReplyKeyboardMarkup()
            markup.add(types.KeyboardButton('Go back'))
            await bot.send_message(message.chat.id, 'Please provide shipping address', reply_markup=markup)
        else:
            state[message.chat.id] = 'choose_options'
            markup = add_options(message.text)
            await bot.send_message(message.chat.id, 'Please choose options', reply_markup = markup)
    elif message.text == 'Go back':
        state[message.chat.id] = 'idle'
        await idle(message)
    else:
        markup = add_items()
        if markup is not None:
            await bot.send_message(message.chat.id, 'Please choose one of the items below or go back', reply_markup = markup)
        else:
            await bot.send_message(message.chat.id, 'There is nothing in the store right now. Come later!')
            state[message.chat.id] = 'idle'
            await idle(message)


@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'choose_options')
async def choose_options(message):
    menu = get_items_from_table(extract(promts_file))
    order = order_requests[message.chat.id]
    options = menu[order.text]
    if message.text in options:
        order.options=[message.text]
        state[message.chat.id] = 'choose_address'
        markup = types.ReplyKeyboardMarkup()
        markup.add(types.KeyboardButton('Go back'))
        await bot.send_message(message.chat.id, 'Please provide shipping address', reply_markup=markup)
    elif message.text == 'Go back':
        state[message.chat.id] = 'order'
        await take_order(message)
    else:
        await bot.send_message(message.chat.id, 'Please choose one of the items below or go back')

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'choose_address')
async def choose_address(message):
    if message.text == 'Go back':
        state[message.chat.id] = 'order'
        await take_order(message)
    else:
        order_requests[message.chat.id].address = message.text
        state[message.chat.id] = 'choose_time'
        markup = types.ReplyKeyboardMarkup()
        markup.add(types.KeyboardButton('Go back'))
        await bot.send_message(message.chat.id, 'Please choose time of the delivery. Ex. at "12:34", "in 10 minutes"', reply_markup=markup)

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'choose_time')
async def choose_time(message):
    if message.text == 'Go back':
        state[message.chat.id] = 'choose_address'
        await choose_address(message)

    else:
        order_requests[message.chat.id].time = message.text
        state[message.chat.id] = 'choose_receiver'
        markup = types.ReplyKeyboardMarkup()
        markup.add(types.KeyboardButton('Go back'))
        await bot.send_message(message.chat.id, "Heyyy, just pick who’s gonna get this delivery... Or Amount... if it's you, just say 'me' or somethin'. Get creative with it!", reply_markup=markup)
        # await choose_receiver(message)

@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'choose_receiver')
async def choose_receiver(message):
    if message.text == 'Go back':
        state[message.chat.id] = 'choose_time'
        await choose_time(message)
    else:
        order_requests[message.chat.id].user = message.text
        state[message.chat.id] = 'confirm_order'
        await confirm_order(message)


@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'confirm_order')
async def confirm_order(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Confirm', callback_data='confirm order'))
    markup.add(types.InlineKeyboardButton('Cancel', callback_data='cancel'))
    name, lastname = get_row_by_id(call.from_user.id)[0:2]
    order = order_requests[call.chat.id]
    if order.options is None:
        message = f'Checkout:\nOrder for {name} {lastname}:\n{order.text}\nADDRESS:\n{order.address}\nAT TIME:{order.time}\nTO WHOM/Amount:{order.user}'
    else:
        message = f'Checkout:\nOrder for {name} {lastname}:\n{order.text}\nOptions:\n'+'\n'.join(order.options)+f'ADDRESS:\n{order.address}\nAT TIME:{order.time}\nTO WHOM:{order.user}'
    await bot.send_message(call.chat.id, message, reply_markup=markup)


@bot.message_handler(func=lambda message: state.get(message.chat.id) == 'add score')
async def add_score(message):
    events = extract_promts(promts_file)['Events']
    markup = types.InlineKeyboardMarkup()
    for event in events['events']:
        markup.add(types.InlineKeyboardButton(event, callback_data = f'event: {event}'))
    markup.add(types.InlineKeyboardButton('Cancel', callback_data='cancel'))
    await bot.send_message(message.chat.id, 'For which event?', reply_markup=markup)


@bot.message_handler(content_types=['photo', 'video'])
async def check_attached(message):
    order = score_orders.get(message.chat.id)
    if order is not None and None not in [order.score, order.user, order.event]:
        await bot.reply_to(message, "Your results are forwarded to our team.")
        text = f'Score for {order.user} \ntask:{order.event} \nscore: {order.score} \ncaption:{message.caption}'
        await group_send_score(message, adds=text)
    else:
        await bot.reply_to(message, "The message is not a desired media ...")

@bot.callback_query_handler(func=lambda call: call.data.startswith('event'))
async def event(call):
    score_orders[call.message.chat.id] = Score(call.data[7:], None, get_username(call.message.chat.id))
    markup = types.InlineKeyboardMarkup()
    for x in range(10, 101, 10):
        markup.add(types.InlineKeyboardButton(str(x), callback_data=f'score: {x}'))
    markup.add(types.InlineKeyboardButton('Cancel', callback_data='cancel'))
    await bot.send_message(call.message.chat.id, 'How many points do you want?', reply_markup=markup)
    await bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('score'))
async def score(call):
    score_orders[call.message.chat.id].score = call.data[7:]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Cancel', callback_data='cancel'))
    await bot.send_message(call.message.chat.id, 'Please attach the proof', reply_markup=markup)
    await bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
async def go_back(call):
    state[call.message.chat.id] = 'idle'
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await idle(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'confirm order')
async def confirm(call):
    # order = order_requests[call.from_user.id]
    # message = f'Checkout:\nOrder for {name} {lastname}:\n{order.text}\nADDRESS:\n{order.address}\nAT TIME:{order.time}'
    await group_send_order((call.from_user.id, call.message.text))
    await go_back(call)

@bot.message_handler(chat_types = ['private'])
async def all_time(message):
    await bot.send_message(message.chat.id, 'If ya get a bit lost in the sauce and need a hand, just slam that /help button, mate!')

#-----------------------------------------------------------------------------------------------
group_bot = AsyncTeleBot(token='6741398055:AAF-Z2mupJxXiGNDgrAAGYfIHY1UVW1rz2A')

async def group_send_order(order):
    id, message = order
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Take order', callback_data='take_order'))
        markup.add(types.InlineKeyboardButton('Delete order', callback_data='done'))
        await bot.send_message(id, 'Your order is received')
        sent_message = await group_bot.send_message(chat_to_send, message, reply_markup = markup)
        orders.add((sent_message.message_id, id))
    except Exception as e:
        print(f"Group_send_order fail: {e}")

async def group_send_score(message, adds = '', mark=True):
    try:
        markup = types.InlineKeyboardMarkup()
        if mark:
            markup.add(types.InlineKeyboardButton('accept', callback_data='accept'))
            markup.add(types.InlineKeyboardButton('decline', callback_data='decline'))
        file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        sent_msg = None
        new_caption = adds if message.caption is None else adds + ' ' + message.caption
        # Send the media with caption as an echo message
        if message.content_type == 'photo':
            sent_msg = await group_bot.send_photo(chat_to_send, downloaded_file, caption=new_caption, reply_markup= markup)
        elif message.content_type == 'video':
            sent_msg = await group_bot.send_video(chat_to_send, downloaded_file, caption=new_caption, reply_markup= markup)
        # Send the message text to the specified user

        # sent_msg = await group_bot.send_message(chat_to_send, message_text, parse_mode='Markdown', reply_markup=markup)
        if sent_msg is not None and mark: score_requests.add((sent_msg.message_id, message))

        return sent_msg
    except Exception as e:
        print(f"Group_send_order fail: {e}")



@group_bot.message_handler(commands=['start'])
async def group_start(message):
    await group_bot.send_message(message.chat.id, 'This is a bot for taking orders and evaluation scores. New tasks are coming!')

@group_bot.callback_query_handler(func=lambda call: call.data == "take_order")
async def group_handle_take_order(call):
    """Handles take order button press"""
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Pass order', callback_data='resend_order'))
        markup.add(types.InlineKeyboardButton('Delete order', callback_data='done'))
        # Forward the message to the user who clicked
        # await group_bot.forward_message(call.from_user.id, call.message.chat.id, call.message.message_id)
        time = datetime.fromtimestamp(call.message.date).strftime('%d-%m %H:%M')
        sent_msg = await group_bot.send_message(call.from_user.id, call.message.text + f'\nSent at: {time}', reply_markup = markup)
        msg_id, id = None, None
        for item in orders:
            if item[0] == call.message.message_id:
                await bot.send_message(item[1], 'Your order is on its way!')
                msg_id, id = item

        if msg_id is not None and id is not None:
            orders.remove((msg_id, id))
            orders.add((sent_msg.message_id, id))

        # Delete the original message
        await group_bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Error taking order : {e}")


@group_bot.callback_query_handler(func=lambda call: call.data == "accept")
async def group_accept_order(call):
    """Handles score accept button press"""
    try:
        score_requests_ = copy.copy(score_requests)
        msg_id, msg = None, None
        for item in score_requests_:
            if item[0] == call.message.message_id:
                msg_id, msg = item
                await bot.reply_to(msg, 'Your score update was accepted!')
                score = 0
                for line in call.message.caption.split('\n'):
                    if line.startswith('score:'):
                        score = int(line.split()[-1])
                        update_score(msg.from_user.id, score)
                        name, lastname = get_username(msg.from_user.id)
                        await group_send_score(msg, mark=False, adds=f'Score updated for {name} {lastname}: {score} \ncaption:')
                        break

        if msg_id is not None and msg is not None:
            score_requests.remove((msg_id, msg))


        # Delete the original message
        await group_bot.delete_message(chat_to_send, call.message.message_id)

    except Exception as e:
        print(f"Error accepting score update : {e}")

@group_bot.callback_query_handler(func=lambda call: call.data == "decline")
async def group_decline_order(call):
    """Handles score decline button press"""
    try:
        msg_id, id = None, None
        for item in score_requests:
            if item[0] == call.message.message_id:
                await bot.reply_to(item[1], 'Your score update was declined!')
                msg_id, id = item

        if msg_id is not None and id is not None:
            score_requests.remove((msg_id, id))


        # Delete the original message
        await group_bot.delete_message(chat_to_send, call.message.message_id)
    except Exception as e:
        print(f"Error declining score update : {e}")

@group_bot.callback_query_handler(func=lambda call: call.data == "done")
async def group_handle_delete_order(call):
    """Handles take order button press"""
    try:
        # Delete the original message
        await group_bot.send_message(1818197126, call.message.text)
        await group_bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Error in group_handle_delete_order : {e}")



@group_bot.callback_query_handler(func=lambda call: call.data == "resend_order")
async def group_abandon_order(call):
    """Handles abandon button press"""
    try:
        await group_bot.send_message(call.from_user.id, 'Abandoned order')

        # # Forward the message to the user who clicked
        # await group_bot.forward_message(chat_to_send, call.message.chat.id, call.message.message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Take order', callback_data='take_order'))
        sent_msg = await group_bot.send_message(chat_to_send, call.message.text, reply_markup = markup)
        msg_id, id = None, None
        for item in orders:
            if item[0] == call.message.message_id:
                msg_id, id = item

        if msg_id is not None and id is not None:
            orders.remove((msg_id, id))
            orders.add((sent_msg.message_id, id))
        # Delete the original message
        await group_bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        print(f"Error deleting or forwarding message: {e}")

#-----------------------------------------------------------------------------------------------
print(
    'Start polling'
)
called_start = False

async def start():
    # Your code in start(), including asynchronous calls
    global called_start  # Access the global variable
    called_start = True
    await bot.delete_webhook()  # Now using await
    await group_bot.delete_webhook()  # Now using await

async def main():
    if not called_start:  # Check if start has been called
        await start()

    await asyncio.gather(bot.polling(), group_bot.polling())

asyncio.run(main())
aiohttp.ClientSession().close()
