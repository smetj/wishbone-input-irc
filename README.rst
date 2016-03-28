::

              __       __    __
    .--.--.--|__.-----|  |--|  |--.-----.-----.-----.
    |  |  |  |  |__ --|     |  _  |  _  |     |  -__|
    |________|__|_____|__|__|_____|_____|__|__|_____|
                                       version 2.1.2

    Build composable event pipeline servers with minimal effort.


    ==================
    wishbone.input.irc
    ==================

    Version: 1.0.0

    Joins an IRC channel to accept input.
    -------------------------------------


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

