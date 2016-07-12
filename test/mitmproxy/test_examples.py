import glob
import json
import mock
import os
import sys
from contextlib import contextmanager

from mitmproxy import script
import netlib.utils
from netlib import tutils as netutils
from netlib.http import Headers
from . import tutils

example_dir = netlib.utils.Data(__name__).path("../../examples")


@contextmanager
def example(command):
    command = os.path.join(example_dir, command)
    with script.Script(command) as s:
        yield s


@mock.patch("mitmproxy.ctx.master")
@mock.patch("mitmproxy.ctx.log")
def test_load_scripts(log, master):
    scripts = glob.glob("%s/*.py" % example_dir)

    for f in scripts:
        if "har_extractor" in f:
            continue
        if "flowwriter" in f:
            f += " -"
        if "iframe_injector" in f:
            f += " foo"  # one argument required
        if "filt" in f:
            f += " ~a"
        if "modify_response_body" in f:
            f += " foo bar"  # two arguments required

        s = script.Script(f)
        try:
            s.load()
        except Exception as v:
            if "ImportError" not in str(v):
                raise
        else:
            s.unload()


def test_add_header():
    flow = tutils.tflow(resp=netutils.tresp())
    with example("add_header.py") as ex:
        ex.run("response", flow)
        assert flow.response.headers["newheader"] == "foo"


@mock.patch("mitmproxy.contentviews.remove")
@mock.patch("mitmproxy.contentviews.add")
def test_custom_contentviews(add, remove):
    with example("custom_contentviews.py"):
        assert add.called
        pig = add.call_args[0][0]
        _, fmt = pig(b"<html>test!</html>")
        assert any(b'esttay!' in val[0][1] for val in fmt)
        assert not pig(b"gobbledygook")
    assert remove.called


def test_iframe_injector():
    with tutils.raises(script.ScriptException):
        with example("iframe_injector.py"):
            pass

    flow = tutils.tflow(resp=netutils.tresp(content=b"<html>mitmproxy</html>"))
    with example("iframe_injector.py http://example.org/evil_iframe") as ex:
        ex.run("response", flow)
        content = flow.response.content
        assert b'iframe' in content and b'evil_iframe' in content


def test_modify_form():
    form_header = Headers(content_type="application/x-www-form-urlencoded")
    flow = tutils.tflow(req=netutils.treq(headers=form_header))
    with example("modify_form.py") as ex:
        ex.run("request", flow)
        assert flow.request.urlencoded_form[b"mitmproxy"] == b"rocks"

        flow.request.headers["content-type"] = ""
        ex.run("request", flow)
        assert list(flow.request.urlencoded_form.items()) == [(b"foo", b"bar")]


def test_modify_querystring():
    flow = tutils.tflow(req=netutils.treq(path=b"/search?q=term"))
    with example("modify_querystring.py") as ex:
        ex.run("request", flow)
        assert flow.request.query["mitmproxy"] == "rocks"

        flow.request.path = "/"
        ex.run("request", flow)
        assert flow.request.query["mitmproxy"] == "rocks"


def test_modify_response_body():
    with tutils.raises(script.ScriptException):
        with example("modify_response_body.py"):
            assert True

    flow = tutils.tflow(resp=netutils.tresp(content=b"I <3 mitmproxy"))
    with example("modify_response_body.py mitmproxy rocks") as ex:
        assert ex.ns["state"]["old"] == b"mitmproxy" and ex.ns["state"]["new"] == b"rocks"
        ex.run("response", flow)
        assert flow.response.content == b"I <3 rocks"


def test_redirect_requests():
    flow = tutils.tflow(req=netutils.treq(host=b"example.org"))
    with example("redirect_requests.py") as ex:
        ex.run("request", flow)
        assert flow.request.host == "mitmproxy.org"


@mock.patch("mitmproxy.ctx.log")
def test_har_extractor(log):
    if sys.version_info >= (3, 0):
        with tutils.raises("does not work on Python 3"):
            with example("har_extractor.py -"):
                pass
        return

    with tutils.raises(script.ScriptException):
        with example("har_extractor.py"):
            pass

    times = dict(
        timestamp_start=746203272,
        timestamp_end=746203272,
    )

    flow = tutils.tflow(
        req=netutils.treq(**times),
        resp=netutils.tresp(**times)
    )

    with example("har_extractor.py -") as ex:
        ex.run("response", flow)

        with open(tutils.test_data.path("data/har_extractor.har")) as fp:
            test_data = json.load(fp)
            assert json.loads(ex.ns["context"].HARLog.json()) == test_data["test_response"]
