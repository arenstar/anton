from anton import commands
from anton import db
from anton import events
from anton import http
import re
import cgi

DB = db.LowercaseDB("learndb")


class BadQuotedDataException(Exception):
    pass


class LookupException(Exception):
    pass


def quote_parse(key, value):
    if key[0] == "\"":
        v = ("%s %s" % (key[1:], value)).split("\" ", 1)
        if len(v) < 2:
            raise BadQuotedDataException
        key, value = v
    return key, value


@commands.register(["!add", "++"])
def add(callback, key, value):
    try:
        key, value = quote_parse(key, value)
    except BadQuotedDataException:
        return "bad quoted data"

    DB[key] = value
    return "got it!"


@commands.register("--")
def remove(callback, key):
    if key not in DB:
        return "doesn't exist!"

    del DB[key]
    return "deleted"


def lookup(key, follow=True, return_key=False):
    value = DB.get(key)
    if value is None:
        raise KeyError

    if not follow:
        if return_key:
            return key
        return value

    stack = [key]
    while True:
        if not value.startswith("@link "):
            if return_key:
                return key
            return value

        new_key = value[6:]
        if new_key in stack:
            raise LookupException("error: @link loop at %s (stack: %s)" % (key, repr(stack)))
        stack.append(new_key)

        value = DB.get(new_key)
        if value is None:
            raise LookupException("error: @link broken at %s (stack: %s)" % (key, repr(stack)))


@commands.register("anton:")
def query_bot(callback, key):
    try:
        value = lookup(key)
    except KeyError:
        return events.CONTINUE
    except LookupException:
        return events.CONTINUE

    return value


@commands.register("??")
def query(callback, key):
    try:
        value = lookup(key)
    except KeyError:
        return "doesn't exist"
    except LookupException, e:
        return e.args[0]

    return value


@commands.register("&&")
def query_no_follow(callback, key):
    try:
        value = lookup(key, follow=False)
    except KeyError:
        return "doesn't exist"
    except LookupException, e:
        return e.args[0]

    return value


@commands.register("++a")
def append(callback, key, value):
    try:
        key, value = quote_parse(key, value)
    except BadQuotedDataException:
        return "bad quoted data"

    try:
        key = lookup(key, return_key=True)
    except KeyError:
        return "doesn't exist"
    except LookupException, e:
        return e.args[0]

    DB[key] = DB[key] + value
    return "done"


@events.register("join")
def on_join(type, irc, obj):
    nick = obj["source"]["nick"]

    try:
        value = lookup(nick)
    except KeyError:
        return

    irc.chanmsg(obj["channel"], "[%s] %s" % (nick, value))


@http.register(re.compile("^/learndb$"))
def http_handler(env, m, irc):
    t = [u"<html><head><title>learndb index</title></head><body><table><tbody>"]
    for key, value in DB.iteritems():
        t.append(u"<tr><td><b>%s</b></td><td>%s</td></tr>" % (cgi.escape(key), cgi.escape(value)))

    t.append(u"</tbody></table></body></html>")
    return "text/html", u"\n".join(t).encode('utf-8')
