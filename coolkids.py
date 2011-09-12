#!/usr/bin/python
import urllib
import re
import difflib
import redis
import random
import string
from BeautifulSoup import BeautifulSoup

THRESHOLD = .9

def random_key():
    random.seed()
    d = [random.choice(string.ascii_lowercase + string.digits) for x in xrange(20)]
    s = "".join(d)
    return s

def open_url(url):
    return urllib.urlopen(url).read()

def get_script_tags(html):
    try:
        soup = BeautifulSoup(html)
        return soup('script')
    except:
        return []

def add_new_script(rdis, script, domain):
    key = random_key()
    domain_key = "%s:domains" % key
    rdis.hset(key, 'script', script)
    rdis.hset(key, 'domains', domain_key)
    rdis.lpush(domain_key, domain)
    rdis.zadd('scripts', key, 0)

def increment_script(rdis, script_key, domain):
    # Increment the script's score by 1
    print 'I am incrementing'
    print script_key
    rdis.zincrby('scripts', script_key, 1)
    # Record the domain name
    domain_key = "%s:domains" % script_key
    rdis.lpush(domain_key, domain)

def detect_google_analytics(html):
    scripts = get_script_tags(html)
    for script in scripts:
        print str(script)
        if re.search("google-analytics\.com\/ga\.js", str(script)):
            return True
        if re.search("_getTracker\(\".*\"\);", str(script)):
            return True
    return False

def iter_islast(iterable):
    """ iter_islast(iterable) -> generates (item, islast) pairs

Generates pairs where the first element is an item from the iterable
source and the second element is a boolean flag indicating if it is the
last item in the sequence.
"""

    it = iter(iterable)
    prev = it.next()
    for item in it:
        yield prev, False
        prev = item
    yield prev, True

if __name__ == '__main__':

    rdis = redis.Redis(host='localhost', port=6379, db=4)

    urls = ['http://www.marksanborn.net',
            'http://github.com',
            'http://yahoo.com',
            'http://news.ycombinator.com',
            'http://www.google.com',
            'http://twitter.com',
            'http://facebook.com',
            'http://ebay.com',
            'http://reddit.com',
            'http://gmail.com',
            'http://youtube.com',
            'http://wikipedia.org',
            'http://www.amazon.com',
            ]

    for url in urls:

        # Open the url and extract out the html
        html = open_url(url)
        print 'done getting html'

        # get all the script tags
        script_tags = get_script_tags(html)

        # look in the db for matches greater than x percent
        for script in script_tags:
            stored_scripts = rdis.zrange('scripts', 0, -1)

            if stored_scripts == []:
                add_new_script(rdis, str(script), url)
            else:
                length = len(stored_scripts)
                for i, stored_script_key in enumerate(stored_scripts):
                    stored_script = rdis.hget(stored_script_key, 'script')
                    ratio = difflib.SequenceMatcher(None, str(script), stored_script).ratio()
                    print ratio
                    # if we have a match increment the zscore of the set and record domain name
                    if ratio > THRESHOLD:
                        print "incrementing %s" % stored_script_key
                        increment_script(rdis, stored_script_key, url)
                        print 'breaking'
                        break

                    # if we do not have a significant match
                    # add new script
                    print i
                    print length - 1
                    if i == (length - 1):
                        add_new_script(rdis, str(script), url)
                        print 'iterislast is getting ran'

