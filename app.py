import time

import redis
import functools
import math
import xml.etree.ElementTree as ET
from flask import Flask
from flask import Response
from redis.connection import Encoder

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)
first_name = 0
last_name = 1
student_number = 2
test_id = 3

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello Stile Assessors! I have been seen {} times.\n'.format(count)

@app.route('/results')
def results():
    value = ""
    tree = ET.parse('sample_results.xml')
    root = tree.getroot()
    for result in root.iter('mcq-test-result'):
        value += result[first_name].text + " " + result[last_name].text + ": "
        for summary in result.iter(tag = 'summary-marks'):
            score = int(summary.attrib['obtained'])
            value += str(score) + '\n'

    return value

@app.route('/results/<int:testid>/aggregate')
def index(testid=1):
    pass
    #list of submission names to ensure
    scores_names = {}
    scores = []
    names = []
    available_marks = 20
    value = ""
    tree = ET.parse('sample_results.xml')
    root = tree.getroot()
    #getting all of the test results
    for result in root.iter('mcq-test-result'):
        if data_fails_check(result):
            continue

        if int(result[test_id].text) == testid:
            name = result[student_number].text
            names.append(name)
            for summary in result.iter(tag = 'summary-marks'):

                #here we ensure that duplicate ID entries have their highest score taken
                if name in scores_names:
                    if scores_names[name] < int(summary.attrib['obtained']):
                        scores_names[name] = int(summary.attrib['obtained'])
                if name not in scores_names:
                    scores_names[name] = int(summary.attrib['obtained'])
                # here is where we can put a check to make sure the
                # number of questions match the expected
                if int(summary.attrib['available']) != available_marks:
                    print("wrong test?")
    #checks to make sure there are test results in the dict
    if len(scores_names) < 1:
        return Response("no results found with that test ID", status=400)
    #convert dict into a list for below calculations
    scores = list(scores_names.values())
    number_of_scores = len(scores)
    scores.sort()
    min_score = scores[0]
    max_score = scores[-1]
    total_score:float = 0
    for score in scores:
        total_score = total_score + float(score)
    #total score divided by number for mean, divide by available marks and times 100 for percentage
    mean:float = total_score/number_of_scores/available_marks*100
    #see below for where percentile came from
    p25 = percentile(scores, percent = 0.25)
    p50 = percentile(scores, percent = 0.5)
    p75 = percentile(scores, percent = 0.75)

    values = {
        'mean': mean, 
        'min': min_score, 
        'max': max_score, 
        'count': number_of_scores,
        'p25': p25,
        'p50': p50,
        'p75': p75,
        }

    return values

#shamelessly grabbed from https://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/ 
#I wanted to use numpy but I couldn't figure out how to ensure it was inclued with docker build :) 
def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

def data_fails_check(element):
    result = False
    #this is where I would put my data integrity rules
    if not hasattr(element, "tag"):
        result = True
    if result == True:
        print("sorry this one failed")
        #here is where I would put the print output for the poor intern to manually handle
    return result