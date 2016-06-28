# -*- coding: utf-8 -*-
import time
import argparse
import sys
from datetime import timedelta

try:
    from HTMLParser import HTMLParser
    from urlparse import urljoin, urldefrag
except ImportError:
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urldefrag

from tornado import httpclient, gen, ioloop, queues, httputil


concurrency, total = 100, 1000

def parse_arguments():
    parser = argparse.ArgumentParser(description='Multi test remoate api')

    parser.add_argument("url", metavar='URL', type=str, nargs=1, help="Remote url")
    parser.add_argument("-H", "--header", metavar='LINE', action="append", dest="headers", type=str, nargs=1, help="Pass custom header LINE to server (H)")
    parser.add_argument("-d", "--data", metavar='DATA', action="append", dest="datas", type=str, nargs=1, help="HTTP POST data (H)")
    parser.add_argument("--compressed", dest="compressed", action='store_const', const=True, default=False, help="Request compressed response (using deflate or gzip)")

    return parser.parse_args()

args = parse_arguments()
headers = httputil.HTTPHeaders()
[headers.parse_line(hs[0]) for hs in args.headers or []]
datas = [ds[0] for ds in args.datas or []]
method = "POST" if datas else "GET"
body = None if not datas else "&".join(datas)
url = args.url[0]
compressed = args.compressed

@gen.coroutine
def main():
    q = queues.Queue()
    used = queues.Queue()

    #@gen.coroutine
    def push():
        for i in range(total):
            q.put(i) #yield q.put(i)
    push()

    start = time.time()

    @gen.coroutine
    def fetch_url():
        aid = yield q.get()
        try:
            asynclient = httpclient.AsyncHTTPClient()
            response = yield asynclient.fetch(url, method=method, headers = headers, body = body, follow_redirects=False)

            #html = response.body if isinstance(response.body, str) \
            #    else response.body.decode()
            html = response.body

        except Exception as e:
            print('Exception: %s %s' % (e, url))

        finally:
            q.task_done()

    @gen.coroutine
    def worker():
        while True:
            yield fetch_url()

    for _ in range(concurrency):
        worker()

    yield q.join(timeout=timedelta(seconds=300))
    print('Done in {0:.3f} seconds'.format(time.time() - start))

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    io_loop = ioloop.IOLoop.current()
    io_loop.run_sync(main)

