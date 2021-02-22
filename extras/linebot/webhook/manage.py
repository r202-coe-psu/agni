from flask import Flask, request, abort
app = Flask(__name__)
from linebot import (
LineBotApi, WebhookHandler
)
from linebot.exceptions import (
InvalidSignatureError
)
from linebot.models import (
AudienceRecipient,MessageEvent, TextMessage, TextSendMessage, FollowEvent, UnfollowEvent
)
line_bot_api = LineBotApi('EkvnEeLrg5GGBEQLJ6hPiScVtR7i71WU7NSoIJdVIbTnRV5PP2K1ppm+PPw9NrZFcAld/ZdB/1pzv7nctnqQ1JrsnQxNq/WDTZZbfIk+1eB+Naz+nCAHNVAIA/6l0HCP4KYoheTxzdhMGrw1DD95bwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bb83b14d1fd296494cd98c5979a32227')

@app.route('/')
def index():
    return 'Hello World!'

@app.route('/webhook', methods=['GET','POST'])
def webhook():
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
    return 'Connection'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print('got message')
    line_bot_api.reply_message(
    event.reply_token,
    TextSendMessage(text=event.message.text))
    #test sending different message based on user
    line_bot_api.push_message('U42de329adb21e5346a18ad276be9cf92', TextSendMessage(text='p1'))
    line_bot_api.push_message('U55d64e7dc8e61b235b88aa0a403df2f9', TextSendMessage(text='p2'))

@handler.add(FollowEvent)
def handle_follow(event):
    print('got follow event')
    print('id ', event.source.user_id)
    ### add to database


    ###

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    print('got unfollow event')
    ### remove from database

    
    ###
    
if __name__ == '__main__':
    app.run(debug=True)