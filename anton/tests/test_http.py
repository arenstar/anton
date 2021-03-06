# -* coding: utf-8 *-
import re
import socket
import unittest
import gevent.monkey
import mock
import requests
from .test_irc import TestIRCServer
from anton import http, irc_client


class TestHTTPConnector(unittest.TestCase):
    """
    This tests anton's HTTP stack by requesting a HTTP URL from the built-in HTTP server which in turn sends
    an IRC message through the IRC client to our test IRC server implementation. On the way back we also
    verify that anton's built-in HTTP server returned the HTTP response with the correct content-type and
    content.
    """
    @classmethod
    def setUpClass(cls):
        gevent.monkey.patch_socket()

    @classmethod
    def tearDownClass(cls):
        # remove monkey patching
        reload(socket)

        if not gevent.wait(timeout=5):
            raise Exception("TestHTTPConnector left hanging Greenlets")

    def tearDown(self):
        http.HANDLERS = []  # remove all registered handlers so they don't influence other tests

    def test_http_hook(self):
        @http.register(re.compile("^/thumbsup$"))
        def httptest(wsgi_env, regex_match, irc_client_instance):
            irc_client_instance.chanmsg("#test", "Eeey!")
            return "text/plain", "Success"

        ircserver = TestIRCServer("Eeey!", ('127.0.0.1', 0))
        ircserver.start()
        ircclient = irc_client.IRC(max_reconnects=1, max_messages=3)

        import anton
        anton.config.BACKEND = ("127.0.0.1", ircserver.server_port)
        ircclient.start()

        anton.config.HTTP_LISTEN = "127.0.0.1", 0
        http_server = http.server(ircclient)
        http_server.start()
        result = requests.get("http://127.0.0.1:%s/thumbsup" % http_server.server_port)
        self.assertTrue(ircserver.message_received)
        self.assertEqual(ircserver.received[-1], "PRIVMSG #test :Eeey!\r\n")
        self.assertEqual(result.text, "Success")
        self.assertEqual(result.headers['Content-type'], "text/plain")
        ircserver.close()
        ircclient.stop()
        http_server.close()

    def test_http_404(self):
        @http.register(re.compile("^/thumbsdown$"))
        def httptest(wsgi_env, regex_match, irc_client_instance):
            return "text/plain", "wat?!"

        import anton
        anton.config.HTTP_LISTEN = "127.0.0.1", 0
        ircclient = mock.Mock()
        http_server = http.server(ircclient)
        http_server.start()
        result = requests.get("http://127.0.0.1:%s/thumbsup" % http_server.server_port)
        self.assertEqual(result.status_code, 404)
        http_server.stop()

    def test_http_autocontenttype(self):
        @http.register(re.compile("^/thumbsup$"))
        def httptest(wsgi_env, regex_match, irc_client_instance):
            return "Eeey!"

        import anton
        anton.config.HTTP_LISTEN = "127.0.0.1", 0
        ircclient = mock.Mock()
        http_server = http.server(ircclient)
        http_server.start()
        result = requests.get("http://127.0.0.1:%s/thumbsup" % http_server.server_port)
        self.assertEqual(result.text, "Eeey!")
        self.assertEqual(result.headers['Content-type'], "text/plain")
        http_server.close()
