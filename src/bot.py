import time
import sys
import telepot
from src.validations import date, hour
from src.database import Database
from telepot.delegate import pave_event_space, per_chat_id, create_open
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

InitialKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Today", callback_data="day"),
     InlineKeyboardButton(text="This Week", callback_data="week"),
     InlineKeyboardButton(text="This Month", callback_data="month")],

    [InlineKeyboardButton(text="New Event", callback_data="new")]
])

RecurrentKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Daily", callback_data="1"),
     InlineKeyboardButton(text="Working Days", callback_data="2")],

    [InlineKeyboardButton(text="Weekly", callback_data="3"), InlineKeyboardButton(text="Monthly", callback_data="4"),
     InlineKeyboardButton(text="Yearly", callback_data="5"), InlineKeyboardButton(text="Nope", callback_data="0")]
])

AlertKeyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="15 min before", callback_data="-15"),
     InlineKeyboardButton(text="30 min before", callback_data="-30"),
     InlineKeyboardButton(text="Nope", callback_data="0")]
])


class Planner(telepot.helper.ChatHandler):
    def __init__(self, *args, **kargs):
        super(Planner, self).__init__(include_callback_query=True, *args, **kargs)
        self.USER = sys.argv[1]
        self._on_chat = None
        self.event = {}
        self.db = Database()

    def on_chat_message(self, msg):
        print(msg)
        content_type, chat_type, chat_id = telepot.glance(msg)
        if msg['from']['username'] != self.USER and chat_type == "private":
            self.bot.sendMessage(chat_id, "You don't have authorization to talk with me. :(")
            return
        if content_type == "text":
            if self._on_chat is None:
                if msg['text'] == '/start':
                    self.bot.sendMessage(chat_id, 'See your schedule for:', reply_markup=InitialKeyboard)
            else:
                if "new" in self._on_chat:
                    self.new_event(chat_id, msg['text'])

    def on_callback_query(self, msg):
        print(msg)
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        if self._on_chat is not None and "new" in self._on_chat:
            self.new_event(msg['message']['chat']['id'], query_data, query_id)
        elif query_data in ["day", "week", "month"]:
            self.bot.answerCallbackQuery(query_id, text=None)
            self.send_events(msg['message']['chat']['id'], query_data)
        elif query_data == "new":
            self.bot.answerCallbackQuery(query_id, text=None)
            self.new_event(msg['message']['chat']['id'], query_data, query_id)

    def new_event(self, chat_id, text=None, query=None):
        if self._on_chat is None:
            self.bot.sendMessage(chat_id, "Send me: event description, initial and final date, initial and final hour, follow this sample:")
            self.bot.sendMessage(chat_id, "`Some description\nDD/MM/YYYY DD/MM/YYYY\nHH:MM HH:MM`", parse_mode="Markdown")
            self._on_chat = "new1"
        elif self._on_chat == "new1":
            if len(text.split('\n')) == 3:
                description, dates, hours = text.split('\n')
                self.event['description'] = description[0:50]
                self.event['initial_date'], self.event['final_date'] = dates.split(' ')
                self.event['initial_hour'], self.event['final_hour'] = hours.split(' ')
                if date(self.event['initial_date']) and date(self.event['final_date']) and\
                    hour(self.event['initial_hour']) and hour(self.event['final_hour']):
                    self.bot.sendMessage(chat_id, "This event is recurrent?", reply_markup=RecurrentKeyboard)
                    self._on_chat = "new2"
                else:
                    self.bot.sendMessage(chat_id, "Something wrong with the data format, try again")
            else:
                self.bot.sendMessage(chat_id, "Something wrong with the data format, try again")
        elif self._on_chat == "new2":
            self.event['recurrence'] = text
            if text != '0':
                self.bot.sendMessage(chat_id, "How many cycles?")
                self._on_chat = "new3"
            else:
                self.event['cycles'] = 0
                self._on_chat = "new4"
                self.new_event(chat_id, text, query)

        elif self._on_chat == "new3":
            self.event['cycles'] = text
            self._on_chat = "new4"
            self.new_event(chat_id, text, query)

        elif self._on_chat == "new4":
            self.bot.sendMessage(chat_id, "You want that I remember you?", reply_markup=AlertKeyboard)
            self._on_chat = "new5"

        elif self._on_chat == "new5":
            self.event['alert'] = text
            message = "Ops, something wrong has happened.\nTry again later!"
            if self.db.new_event(self.event):
                message = "Great, event scheduled!!"
                self._on_chat = None
            self.bot.answerCallbackQuery(query, message, show_alert=True)

    def send_events(self, chat, period):
        pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Incorrect usage")
        print("Try `python {} ALLOWED_USER BOT_TOKEN`".format(sys.argv[0]))
        sys.exit(-1)
    bot = telepot.DelegatorBot(sys.argv[2], [
        pave_event_space()(
            per_chat_id(), create_open, Planner, timeout=60),
    ])
    MessageLoop(bot).run_as_thread()
    print("Listening...")
    while True:
        time.sleep(10)
