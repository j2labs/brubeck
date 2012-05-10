# ZeroMQ

ZeroMQ, aka ZMQ, is essentially a sockets framework. It makes it easy to build
messaging topologies across different types of sockets. They also are language
agnostic by way of having driver implementations in every language: Scheme, 
Java, C, Ruby, Haskell, Erlang; and Brubeck uses the Python driver.

It is common for service oriented architectures to be constructed with HTTP
interfaces, but Brubeck believes ZMQ is a more suitable tool. It provides
multiple message distribution patterns and lets you open multiple types of
sockets. 


## Simple Examples

Here is a simple job distributor. It passes messages round-robin to any
connected hosts.

    import zmq
    import time

    ctx = zmq.Context()
    s = ctx.socket(zmq.PUSH)
    s.bind("ipc://hellostream:5678")

    while True:
        s.send("hello")
        print 'Sending a hello'
        time.sleep(1)

This what a simple consumer could look like. See what happens if you hook up
multiple consumers.

    import zmq
    import datetime

    ctx = zmq.Context()
    s = ctx.socket(zmq.PULL)
    s.connect("ipc://hellostream:5678")
    
    while True:
        msg = s.recv()
        print 'Received:', msg
        

# Brubeck and ZMQ

Brubeck can uses this system when it communicates with Mongrel2. It can also
use this to talk to pools of workers, or AMQP servers, or data mining engines.

ZMQ is part of Brubeck's concurrency pool, so working with it is just like
working with any networked system. When you use Brubeck with Mongrel2, you
communicate with Mongrel2 over two ZMQ sockets.

There is a PUSH/PULL socket that Mongrel2 uses to send messages to handlers,
like Brubeck. An added bonus is that PUSH/PULL sockets automatically load balance
requests between any connected handlers. Add another handler and it is
automatically part of the round robin queue.

When the handlers are ready to respond, they use a PUB/SUB socket, meaning
Mongrel2 subscribes to responses from Brubeck handlers. This can be interesting
for multiple reasons, such as having media served from a single Brubeck handler
to multiple Mongrel2 frontends. 

Having two sockets allows for an interesting messaging topology between Mongrel2
and Brubeck. All of ZeroMQ is available to you for communicating with workers too.
You might enjoy building an image processing system in Scheme and can do so by
opening a ZeroMQ socket in your Scheme process to connect with a Brubeck socket.
ZeroMQ is mostly language agnostic.
