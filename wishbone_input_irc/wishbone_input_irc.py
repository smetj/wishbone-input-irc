#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  wishbone-input-irc.py
#
#  Copyright 2016 Jelle Smet <development@smetj.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

from gevent import monkey; monkey.patch_all()
from gevent import sleep
from wishbone import Actor
from wishbone.event import Event

from bot import SingleServerIRCBot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr


class IRCBot(SingleServerIRCBot):

    def __init__(self, callback, logging, channels, nickname, server, port=6667, password=None):
        SingleServerIRCBot.__init__(self, [(server, port, password)], nickname, nickname)
        self.chans = channels
        self.callback = callback
        self.logging = logging

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        self.logging.info("Connected to server.")
        for channel in self.chans:
            if not channel.startswith('#'):
                channel = "#%s" % (channel)
            c.join(channel)
            self.logging.info("Joined channel %s." % (channel))

    def on_privmsg(self, c, e):
        # self.do_command(e, e.arguments[0])
        self.callback(e)
        return

    def on_pubmsg(self, c, e):
        self.callback(e)
        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    # def do_command(self, e, cmd):
    #     nick = e.source.nick
    #     c = self.connection

    #     if cmd == "disconnect":
    #         self.disconnect()
    #     elif cmd == "die":
    #         self.die()
    #     elif cmd == "stats":
    #         for chname, chobj in self.channels.items():
    #             c.notice(nick, "--- Channel statistics ---")
    #             c.notice(nick, "Channel: " + chname)
    #             users = sorted(chobj.users())
    #             c.notice(nick, "Users: " + ", ".join(users))
    #             opers = sorted(chobj.opers())
    #             c.notice(nick, "Opers: " + ", ".join(opers))
    #             voiced = sorted(chobj.voiced())
    #             c.notice(nick, "Voiced: " + ", ".join(voiced))
    #     elif cmd == "dcc":
    #         dcc = self.dcc_listen()
    #         c.ctcp("DCC", nick, "CHAT chat %s %d" % (
    #             ip_quad_to_numstr(dcc.localaddress),
    #             dcc.localport))
    #     else:
    #         c.notice(nick, "Not understood: " + cmd)


class IRC(Actor):

    '''**Joins an IRC channel to accept input.**

    A simple IRC bot which joins a channel, reads all public and private
    messages and sends these to the module's queues.


    Parameters:

        - server(str)("localhost")
           |  The IRC server to connect to.

        - port(int)(6667)
           |  The IRC server port to connect to.

        - nickname(str)("wishbone")
           |  The bot's nickname.

        - channels(list)(["wishbone"])
           |  The list of channels to join.
           |  Each channel is mapped to a queue.
           |  The queue name has the # portion stripped off.

        - password(str)(None)
           |  The password used to authenticate

    Queues:

        - outbox
           |  The messages of all channels.

        - priv__<nickname>
           |  Receives private messages.

        - <channels>

           |  For each channel in <channels> a queue is created receiving the
           |  messages of only that channel.
    '''

    def __init__(self, actor_config,
                 server="localhost",
                 port=6667,
                 nickname="wishbone",
                 channels=["wishbone"],
                 password=None):
        Actor.__init__(self, actor_config)

        self.pool.createQueue("outbox")

        for channel in self.kwargs.channels:
            self.pool.createQueue(channel)
        self.pool.createQueue("priv__%s" % (nickname))

    def preHook(self):

        self.bot = IRCBot(
            callback=self.handleMessage,
            logging=self.logging,
            channels=self.kwargs.channels,
            nickname=self.kwargs.nickname,
            server=self.kwargs.server,
            port=self.kwargs.port
        )

        self.sendToBackground(self.startBot)

    def postHook(self):

        self.bot.disconnect()

    def startBot(self):

        while self.loop():
            try:
                self.bot.start()
            except Exception as err:
                self.logging.error(err)
                sleep(1)

    def handleMessage(self, message):

        e = Event("\n".join(message.arguments))
        e.set(message.type, '@tmp.%s.type' % (self.name))
        e.set(message.source, '@tmp.%s.source' % (self.name))

        if message.type == "pubmsg":
            e.set(message.target, '@tmp.%s.channel' % (self.name))
            self.submit(e, getattr(self.pool.queue, message.target.strip('#').lower()))
        elif message.type == "privmsg":
            self.submit(e, getattr(self.pool.queue, "priv__%s" % (self.kwargs.nickname)))

        self.submit(e.clone(), self.pool.queue.outbox)


