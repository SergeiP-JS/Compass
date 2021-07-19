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

import db
from config import TOKEN, ADMIN_USERNAME
from common import get_logger, log_func, reply_error
from graph import create_graph
from parser_exchange_rate import parse
from run_check_subscriptions import check


log = get_logger(__file__)


COMMAND_SUBSCRIBE = 'Подписаться'
COMMAND_UNSUBSCRIBE = 'Отписаться'
COMMAND_LAST = 'Последнее значение'
COMMAND_LAST_BY_WEEK = 'За неделю'
COMMAND_LAST_BY_MONTH = 'За месяц'

FILTER_BY_ADMIN=Filters.user(username=ADMIN_USERNAME)


def keyboard_(is_active):
    if is_active:
        COMMANDS = [[COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH], [COMMAND_UNSUBSCRIBE]]
    else:
        COMMANDS = [[COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH], [COMMAND_SUBSCRIBE]]

    return ReplyKeyboardMarkup(COMMANDS, resize_keyboard=True)


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    update.effective_message.reply_html(
        f'Приветсвую {update.effective_user.first_name} 🙂\n'
        'Данный бот способен отслеживать USD валюту и отправлять вам уведомление при изменении 💲.\n'
        'С помощью меню вы можете подписаться/отписаться от рассылки, узнать актуальный курс за день, неделю или месяц.',
        reply_markup=keyboard_(False if not user else user.get().is_active)
    )


@log_func(log)
def on_get_admin_stats(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    first_date=db.ExchangeRate.select().first().date.strftime('%d.%m.%Y')
    last_date=db.ExchangeRate.get_last().date.strftime('%d.%m.%Y')

    update.effective_message.reply_html(
        f'<b>Статистика админа</b>\n\n'
        f'<b>Курсы валют</b>\nКоличество: <b><u>{db.ExchangeRate.select().count()}</u></b>\nДиапазон значений: <b><u>{first_date} - {last_date}</u></b>\n\n'
        f'<b>Подписки</b>\nКоличество активных: <b><u>{db.Subscription.select().where(db.Subscription.is_active == True).count()}</u></b>',
        reply_markup=keyboard_(False if not user else user.get().is_active)
    )


@log_func(log)
def on_command_SUBSCRIBE(update: Update, context: CallbackContext):
    message = update.effective_message
    # print(message.text)

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if not user:
        db.Subscription.create(chat_id=update.effective_chat.id)
        message.text = "Вы успешно подписались 😉"
    else:
        if user.get().is_active:
            message.text = "Подписка уже оформлена 🤔"
        else:
            db.Subscription.set_active(user.get(),True)

            message.text = "Вы успешно подписались 😉"

    message.reply_html(
        message.text,
        reply_markup=keyboard_(user.get().is_active)
    )


@log_func(log)
def on_command_UNSUBSCRIBE(update: Update, context: CallbackContext):
    message = update.effective_message
    # print(message.text)

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if not user:
        message.text = "Подписка не оформлена 🤔"
    else:
        if not user.get().is_active:
            message.text = "Подписка не оформлена 🤔"
        else:
            db.Subscription.set_active(user.get(),False)

            message.text = "Вы успешно отписались 😔"

    message.reply_html(
        message.text,
        reply_markup=keyboard_(False if not user else user.get().is_active)
    )


@log_func(log)
def on_command_LAST(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if db.ExchangeRate.select().first():
        update.effective_message.reply_html(
            f'Актуальный курс USD за <b><u>{db.ExchangeRate.get_last().date}</u></b>: '
            f'{db.ExchangeRate.get_last().value}₽',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот не имеет достаточно информации 😔',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )


@log_func(log)
def on_command_LAST_BY_WEEK(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)
    days=7

    items = [x.value for x in db.ExchangeRate.get_last_by(days=days)]
    if len(items)==days:
        context.bot.send_photo(update.effective_chat.id, open(f'img/graph_{days}.png', 'rb'))
        update.effective_message.reply_html(
            f'Среднее USD за <b><u>неделю</u></b>: {float(sum(items)) / max(len(items), 1)}₽',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот не имеет достаточно информации 😔',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )


@log_func(log)
def on_command_LAST_BY_MONTH(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)
    days=30

    items = [x.value for x in db.ExchangeRate.get_last_by(days=days)]
    if len(items)==days:
        context.bot.send_photo(update.effective_chat.id, open(f'img/graph_{days}.png', 'rb'))
        update.effective_message.reply_html(
            f'Среднее USD за <b><u>месяц</u></b>: {float(sum(items)) / max(len(items), 1)}₽',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )
    else:
        update.effective_message.reply_html(
            'Бот имеет достаточно информации 😔',
            reply_markup=keyboard_(False if not user else user.get().is_active)
        )


@log_func(log)
def on_request(update: Update, context: CallbackContext):
    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    update.effective_message.reply_html(
        'Неизвестная команда 🤔',
        reply_markup=keyboard_(False if not user else user.get().is_active)
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

    Thread(target=check, args=[updater.bot]).start()

    dp = updater.dispatcher

    # Кнопки
    dp.add_handler(CommandHandler('start', on_start,run_async=True))
    dp.add_handler(CommandHandler('admin_stats', on_get_admin_stats, FILTER_BY_ADMIN,run_async=True))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_SUBSCRIBE,run_async=True))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_UNSUBSCRIBE,run_async=True))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST), on_command_LAST,run_async=True))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_LAST_BY_WEEK,run_async=True))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_LAST_BY_MONTH,run_async=True))
    dp.add_handler(MessageHandler(Filters.text('Статистика админа') and FILTER_BY_ADMIN, on_get_admin_stats, run_async=True))
    dp.add_handler(MessageHandler(Filters.text, on_request,run_async=True))

    dp.add_error_handler(on_error)

    updater.start_polling()
    updater.idle()

    log.debug('Finish')


def loop_parse_and_check_graph():
    while True:
        parse()

        items = [x.value for x in db.ExchangeRate.get_last_by(days=7)]
        if len(items) == 7:
            create_graph(7,items)

        items = [x.value for x in db.ExchangeRate.get_last_by(days=30)]
        if len(items) == 30:
            create_graph(30, items)

        time.sleep(8*3600)


if __name__ == '__main__':
     # asyncio.run(async_())
     Thread(target=loop_parse_and_check_graph).start()
     #
     while True:
         try:
             main()
         except:
             log.exception('')
             timeout = 15
             log.info(f'Restarting the bot after {timeout} seconds')
             time.sleep(timeout)

