#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'SPridannikov'


import datetime as DT
import os
import time
from threading import Thread

# pip install python-telegram-bot
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackContext
from telegram.ext.dispatcher import run_async

import db
from config import TOKEN
from common import get_logger, log_func, reply_error
from parser_exchange_rate import parse
from run_check_subscriptions import check_


log = get_logger(__file__)


COMMAND_SUBSCRIBE = 'Подписаться'
COMMAND_UNSUBSCRIBE = 'Отписаться'
COMMAND_LAST = 'Последнее значение'
COMMAND_LAST_BY_WEEK = 'За неделю'
COMMAND_LAST_BY_MONTH = 'За месяц'


def keyboard_(is_active):
    if is_active:
        COMMANDS = [[COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH], [COMMAND_UNSUBSCRIBE]]
    else:
        COMMANDS = [[COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH], [COMMAND_SUBSCRIBE]]

    return ReplyKeyboardMarkup(COMMANDS, resize_keyboard=True)


@run_async
@log_func(log)
def on_start(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)
    
    update.effective_message.reply_html(
        f'Приветсвую {update.effective_user.first_name} 🙂\n'
        'Данный бот способен отслеживать USD валюту и отправлять вам уведомление при изменении 💲.\n'
        'С помощью меню вы можете подписаться/отписаться от рассылки, узнать актуальный курс за день, неделю или месяц.',
        reply_markup=keyboard_(0 if not user else user.get().is_active)
    )


@run_async
@log_func(log)
def on_command_SUBSCRIBE(update: Update, context: CallbackContext):
    message = update.effective_message
    # print(message.text)

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if not user:
        db.Subscription.create(chat_id=update.effective_chat.id, is_active=1, was_sending=0)
        message.text = "Вы успешно подписались 😉"
    else:
        if user.get().is_active:
            message.text = "Подписка уже оформлена 🤔"
        else:
            user_ = user.get()
            user_.is_active = 1
            user_.save()
            user_.modification_datetime = DT.datetime.now()
            user_.save()

            message.text = "Вы успешно подписались 😉"

    message.reply_html(
        message.text,
        reply_markup=keyboard_(user.get().is_active)
    )


@run_async
@log_func(log)
def on_command_UNSUBSCRIBE(update: Update, context: CallbackContext):
    message = update.effective_message
    # print(message.text)

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if not user:
        message.text = "Подписка не оформлена 🤔"
    else:
        if user.get().is_active==0:
            message.text = "Подписка не оформлена 🤔"
        else:
            user_ = user.get()
            user_.is_active = 0
            user_.save()
            user_.was_sending = 0
            user_.save()

            message.text = "Вы успешно отписались 😔"

    message.reply_html(
        message.text,
        reply_markup=keyboard_(user.get().is_active)
    )


@run_async
@log_func(log)
def on_command_LAST(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if db.ExchangeRate.select().first():
        exchange_rate=db.ExchangeRate.get(db.ExchangeRate.id == db.ExchangeRate.select().count())

        update.effective_message.reply_html(
            f'Актуальный курс USD за <b><u>{exchange_rate.date}</u></b>: '
            f'{exchange_rate.value}₽',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот ещё молодой и не имеет достаточно информации 😔',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )


@run_async
@log_func(log)
def on_command_LAST_BY_WEEK(update: Update, context: CallbackContext):
    flag=0
    arr=[]
    i=0

    for val in reversed(db.ExchangeRate.select()):
        if i==7:
            flag=1
            break
        arr.append(val.value)
        i+=1

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if flag:
        update.effective_message.reply_html(
            f'Среднее USD за <b><u>неделю</u></b>: {float(sum(arr)) / max(len(arr), 1)}₽',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот ещё молодой и не имеет достаточно информации 😔',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )


@run_async
@log_func(log)
def on_command_LAST_BY_MONTH(update: Update, context: CallbackContext):
    flag=0
    arr = []
    i = 0

    for val in reversed(db.ExchangeRate.select()):
        if i == 30:
            flag = 1
            break
        arr.append(val.value)
        i += 1

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if flag:
        update.effective_message.reply_html(
            f'Среднее USD за <b><u>месяц</u></b>: {float(sum(arr)) / max(len(arr), 1)}₽',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот ещё молодой и не имеет достаточно информации 😔',
            reply_markup=keyboard_(0 if not user else user.get().is_active)
        )


@run_async
@log_func(log)
def on_request(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    update.effective_message.reply_html(
        'Неизвестная команда 🤔',
        reply_markup=keyboard_(0 if not user else user.get().is_active)
    )


def on_error(update: Update, context: CallbackContext):
    reply_error(log, update, context)


def main():
    cpu_count = os.cpu_count()
    workers = cpu_count
    log.debug('System: CPU_COUNT=%s, WORKERS=%s', cpu_count, workers)

    log.debug('Start')

    updater = Updater(
        TOKEN,
        workers=workers,
        use_context=True
    )

    Thread(target=check_,args=(updater,)).start()

    dp = updater.dispatcher

    # Кнопки
    dp.add_handler(CommandHandler('start', on_start))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_SUBSCRIBE))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_UNSUBSCRIBE))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST), on_command_LAST))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_LAST_BY_WEEK))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_LAST_BY_MONTH))
    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)

    updater.start_polling()
    updater.idle()

    log.debug('Finish')


def parse_():
    while True:
        parse()
        time.sleep(8*3600)


if __name__ == '__main__':
     # asyncio.run(async_())
     Thread(target=parse_).start()
     #
     while True:
         try:
             main()
         except:
             log.exception('')
             timeout = 15
             log.info(f'Restarting the bot after {timeout} seconds')
             time.sleep(timeout)
