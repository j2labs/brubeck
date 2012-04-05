
import sys
import logging
import os
from brubeck.request_handling import Brubeck, WebMessageHandler

from ws4py.framing import Frame, \
    OPCODE_CONTINUATION, OPCODE_TEXT, \
    OPCODE_BINARY, OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG


class WebsocketHandler(WebMessageHandler):

    def websocket(self):
        message = "I like websockets"
        ws_frame = Frame(opcode=OPCODE_TEXT, body=message, masking_key=os.urandom(4), fin=1)
        frame = ws_frame.build()
        return frame
                                  
# test using http://isr.nu/ws/WebSocketTest.htm and point to the server at 
# ws://127.0.0.1:6767/websockets

config = {
    'mongrel2_pair': ('ipc://127.0.0.1:9999', 'ipc://127.0.0.1:9998'),
    'handler_tuples': [(r'^/websockets', WebsocketHandler)],
}
app = Brubeck(**config)
app.run()
