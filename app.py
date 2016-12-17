#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from flask_apscheduler import APScheduler
import pymongo
import json
import datetime
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
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)
# mongodb

mongoclient = pymongo.MongoClient("localhost", 27017)
linedb=mongoclient.linebot
botplace = linedb.place
botlog = linedb.log
bottime = linedb.bottime


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
            'seconds': 60
        }
    ]

    SCHEDULER_API_ENABLED = True

def send(sendid,msg):
    print "push message"
    line_bot_api.push_message(sendid,TextSendMessage(msg))


def job1(a, b):
    #print(str(a) + ' ' + str(b))
    now = datetime.datetime.now()
    #if now.hour==7 and now.minute==45:
    #    send(u'おはようございます。朝の薬のみました？のませました？薬の写真おくってみませんか？')
    #if now.hour==12 and now.minute==45:
    #    send(u'こんにちは。昼の薬のみました？のませました？近況はいかがでしょう?')
    #if now.hour==19 and now.minute==45:
    #    send(u'こんばんは。夜の薬のみました？のませました？お話してみませんか?')
    print now

    items = bottime.find({"hour":now.hour,"minute":now.minute})
    if not isinstance(items,type(None)):
        print "Timer set"
        for item in items:
            print item
            send(item["id"],u"薬のみましたか？のませましたか？\n"+str(now.hour)+u"時"+str(now.minute)+u"分です。"+u"設定された時間です\n"+u"近況はいかがですか？\n")
    

app = Flask(__name__)
app.config.from_object(Config())

scheduler = APScheduler()
# it is also possible to enable the API directly
# scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()

# Line bot
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# help message
helpmessage="""エコーと、打ってから後ろに何か続けると、うった単語を返します
「時間追加8時5分」、指定した時間をセットします
「時間消去8時10分」、指定した時間の設定を削除します
「時間確認」、現在設定されている時間を確認します
「時間全部消去」、設定されている時間をすべて消去します
「またね」、ボットが退出します
"""

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
    source = event.source
    print dir(source)
    print source.as_json_string()
    print source.type
    id = ""
    if source.type == "user":
        id = source.user_id
    elif source.type == "group":
        id = source.group_id
    elif source.type == "room":
        id = source.room_id
    print id
    text = event.message.text
    if re.compile(u"^エコー").search(text):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'あなたは['+event.message.text+u']といいました'))
        source = event.source
        print dir(source)
        #print source.type
        #print source.user_id
        #print("sleep 30sec")
        #time.sleep(30)
        print("send push to ["+source.user_id+"]")
        line_bot_api.push_message(source.user_id,TextSendMessage(text=u'あなたは30秒前に、['+event.message.text+u']といいました'))
        print("finish send push")
    elif re.compile(u"^(おしえて|教えて|ヘルプ|help)$").search(text):
        #line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'エコーと、打ってから後ろに何か続けると、うった単語を返します'))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=helpmessage))
    elif re.compile(u"^(またね)$").search(text):
        if source.type == "room":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'またいつでも呼んでください。ありがとうございました。'))
            line_bot_api.leave_room(id)
            place = botplace.find_one({"id":id})
            print place
            if isinstance(place,type(None)):
                print "leave channel but insert id"
                print botplace.insert_one({"id":id,"type":source.type}).inserted_id
            botplace.update({"id":id},{'$set':{"join":False}})
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'ここからは退出できないようです'))
    elif re.compile(u"^(時間追加|時間設定)[\s]?([0-9]*)(?:時|じ|:|：)([0-9]*)(?:分|ふん)?$").search(text):
        print "Time add"
        print text
        m = re.compile(u"^(時間追加|時間設定)[\s]?([0-9]*)(?:時|じ|:|：)([0-9]*)(?:分|ふん)?$").search(text)
        bottime.insert_one({"id":id,"hour":int(m.group(2)),"minute":int(m.group(3))})
        alltime=""
        for item in bottime.find({"id":id}):
            print item
            alltime=alltime+ str(item["hour"])
            alltime=alltime+ u"時"
            alltime=alltime+ str(item["minute"])
            alltime=alltime+ u"分\n"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'時間追加しました\nいま設定されている時間は以下のようになります\n'+alltime))
    elif re.compile(u"^(時間削除|時間消去)[\s]?([0-9]*)(?:時|じ|:|：)([0-9]*)(?:分|ふん)?$").search(text):
        print "Time delete"
        print text
        m = re.compile(u"^(時間削除|時間消去)[\s]?([0-9]*)(?:時|じ|:|：)([0-9]*)(?:分|ふん)?$").search(text)
        bottime.delete_many({"id":id,"hour":int(m.group(2)),"minute":int(m.group(3))})
        alltime=""
        for item in bottime.find({"id":id}):
            print item
            alltime=alltime+ str(item["hour"])
            alltime=alltime+ u"時"
            alltime=alltime+ str(item["minute"])
            alltime=alltime+ u"分\n"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'時間追加しました\nいま設定されている時間は以下のようになります\n'+alltime))
    elif re.compile(u"^(時間全部消去)$").search(text):
        bottime.delete_many({"id":id})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'設定されている時間を全部消しました'))
    elif re.compile(u"^(時間確認)$").search(text):
        alltime=""
        items=bottime.find({"id":id})
        if not isinstance(items,type(None)):
            for item in items:
                print item
                alltime=alltime+ str(item["hour"])
                alltime=alltime+ u"時"
                alltime=alltime+ str(item["minute"])
                alltime=alltime+ u"分\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'いま設定されている時間は以下のようになります\n'+alltime))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=u'現在設定されている時間はございません\n'+alltime))

        
    print "message json"
    print event.message.as_json_string()
    print "event json"
    print event.as_json_string()
    print "insert to log"
    print linedb.name
    #print botlog.insert_one({"x":10}).inserted_id
    print botlog.insert_one(json.loads(event.as_json_string())).inserted_id
    

# join

@handler.add(JoinEvent)
def handle_join(event):
    source = event.source
    print "join"
    id = ""
    if source.type == "user":
        id = source.user_id
    elif source.type == "group":
        id = source.group_id
    elif source.type == "room":
        id = source.room_id
    print id
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='Joined this ' + event.source.type))    
    print "insert to log raw message"
    print botlog.insert_one(json.loads(event.as_json_string())).inserted_id
    print "check id"
    place = botplace.find_one({"id":id})
    print place
    print type(place)
    if isinstance(place,type(None)):
        print "join channel create insert id"
        print botplace.insert_one({"id":id,"type":source.type}).inserted_id
    else:
        print "already created"
        print dir(place)
    botplace.update({"id":id},{'$set':{"join":True}})


@handler.add(LeaveEvent)
def handle_leave():
    app.logger.info("Got leave event")


@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == 'ping':
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='pong'))


@handler.add(BeaconEvent)
def handle_beacon(event):
    line_bot_api.reply_message(
        event.reply_token,
TextSendMessage(text='Got beacon event. hwid=' + event.beacon.hwid))

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port='9000'
    )
