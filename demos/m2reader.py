#!/usr/bin/env python

import zmq

ctx = zmq.Context()
s = ctx.socket(zmq.PULL)
s.connect("ipc://127.0.0.1:9999")

while True:
    msg = s.recv()
    print msg
