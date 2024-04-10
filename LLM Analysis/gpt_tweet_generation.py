import openai
import os
import json
import numpy as np
import pandas as pd
import time
import sqlalchemy
from tqdm import tqdm
import backoff
import func_timeout
from func_timeout import func_set_timeout
import ast
import json

API_KEY = "sk-"
Overview = "You are an individual who lives in STATE. You enjoy writing Tweets and posting them on Twitter for your followers to read."
Instructions = "Generate 50 Tweets that you might write and post online. Remember that each Tweet has a 280 character limit. Separate each Tweet with a newline character."


@func_set_timeout(60)
def query_GPT(state):
    openai.api_key = API_KEY
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    temperature=0.7,
    top_p=1,
    messages=[
        {"role": "system", "content": Overview.replace("STATE", state)},
        {"role": "user", "content": Instructions}])
    return response["choices"][0]["message"]["content"]

def process_response(response):
    response = response.split("\n")
    try:
        assert len(response) == 50
        assert all([len(tweet) <= 280 for tweet in response])
        assert all([tweet[0].isdigit() for tweet in response])
    except:
        return -1
    #strip newlines and numbers
    response = [tweet.strip() for tweet in response]
    response = [tweet[4:] if tweet[1].isdigit() else tweet[3:] for tweet in response]
    return response
    

@backoff.on_exception(backoff.expo,
                    (openai.error.ServiceUnavailableError, 
                     openai.error.APIConnectionError, 
                     openai.error.APIError,
                     func_timeout.exceptions.FunctionTimedOut),
                    max_tries=3)
def query_GPT_backoff(state):
    response = query_GPT(state)
    response = process_response(response)
    return response


def run_baseline(query_data, index=0):
    results = []
    with open('gpt_generation.txt', 'a') as f:
        if(index == 0): f.write("user_id, STATE, TWEETS\n")
        for i, (user_id, state) in enumerate(tqdm(query_data)):
            if(i < index): continue
            tweets = query_GPT_backoff(state)
            if tweets == -1:
                print("Error in response format at index {}".format(i))
                continue
            results.append((user_id, state, tweets))
            f.write("{}, {}, {}\n".format(str(user_id), state, tweets))
            f.flush()
    return results


def main():
    states = ["New York", "Massachusetts", "Louisiana", "Mississippi"]
    query_data = []
    for state in states:
        for i in range(500):
            user_id = i + (states.index(state) * 500)
            query_data.append((user_id, state))
    results = run_baseline(query_data, index=0) 

main()