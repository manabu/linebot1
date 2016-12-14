#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from flask_apscheduler import APScheduler
import time
import os
import re

# Line bot
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

# check environment value
# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

# job scheduler
class Config(object):
    JOBS = [
        {
            'id': 'job1',
            'func': '__main__:job1',
            'args': (1, 2),
            'trigger': 'interval',
            'seconds': 10
        }
    ]

    SCHEDULER_API_ENABLED = True

def job1(a, b):
    print(str(a) + ' ' + str(b))

app = Flask(__name__)
app.config.from_object(Config())

scheduler = APScheduler()
# it is also possible to enable the API directly
# scheduler.api_enabled = True
scheduler.init_app(app)
# scheduler.start()

# Line bot
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/")
def hello():
    return "Hello World!"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    #line_bot_api.reply_message(
    #    event.reply_token,
    #    TextSendMessage(text=event.message.text))
    text = event.message.text
    if re.compile("^エコー").search(text):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'Hello World! あなたは['+event.message.text+u']といいました'))
        source = event.source
        print dir(source)
        #print source.type
        #print source.user_id
        #print("sleep 30sec")
        #time.sleep(30)
        print("send push to ["+source.user_id+"]")
        line_bot_api.push_message(source.user_id,TextSendMessage(text=u'あなたは30秒前に、['+event.message.text+u']といいました'))
        print("finish send push")


if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port='9000'
    )
