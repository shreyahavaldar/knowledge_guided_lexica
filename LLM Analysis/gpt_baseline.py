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

API_KEY = "sk-"
#Triandis, H. C. (1995). Individualism & collectivism. Westview Press.
Overview = "Given a Tweet, try to reason about whether it reflects the cultural dimension of Individualism or Collectivism. Collectivists are closely linked individuals who view themselves primarily as parts of a whole, be it a family, a network of co-workers, a tribe, or a nation. Such people are mainly motivated by the norms and duties imposed by the collective entity. Individualists are motivated by their own preferences, needs, and rights, giving priority to personal rather than to group goals.\n"
Instructions = "If the Tweet does not reflect either cultural dimension, please label it 'Neither'.\nExample input and output:\nTweet: {Tweet Text}\nLabel: {Individualism, Collectivism, Neither}"


@func_set_timeout(20)
def query_GPT(prompt):
    openai.api_key = API_KEY
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": Overview+Instructions},
        {"role": "user", "content": "Tweet: " + prompt + "\nLabel: "}])
    return response["choices"][0]["message"]["content"]


@backoff.on_exception(backoff.expo,
                    (openai.error.ServiceUnavailableError, 
                     openai.error.APIConnectionError, 
                     func_timeout.exceptions.FunctionTimedOut),
                    max_tries=3)
def query_GPT_backoff(prompt):
    response = query_GPT(prompt)
    return response


def run_baseline(query_data, index=0):
    results = []
    with open('gpt_baseline_results.txt', 'a') as f:
        f.write("index, STATE, TWEET, LABEL\n")
        for i, (tweet, state) in enumerate(tqdm(query_data)):
            if(i < index): continue
            response = query_GPT_backoff(tweet)
            results.append((tweet, state, response))
            f.write("{}, {}, {}, {}\n".format(str(i), state, tweet, response))   
            f.flush()   
    return results

def read_data():
    db_twitter = sqlalchemy.engine.url.URL(drivername='mysql', host='127.0.0.1', database='county_bias', username='shreyah', password='yQ~,K].U^MO1ybD]',port=None, query={'read_default_file': '~/.my.cnf', 'charset':'utf8mb4'})
    engine = sqlalchemy.create_engine(db_twitter)   

    state_codes = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ', 'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
    tweets_2012 = pd.DataFrame()
    for state in state_codes:
        temp = pd.read_sql("SELECT * FROM msgs_10pct_2012_en WHERE state = '{}' LIMIT 2000".format(state), con=engine)
        temp = temp[temp['message'].str.split().str.len() > 5]
        tweets_2012 = pd.concat([tweets_2012, temp.sample(1000, random_state=42)])
        print(state, len(tweets_2012))
            
    tweets_2013 = pd.DataFrame()
    for state in state_codes:
        temp = pd.read_sql("SELECT * FROM msgs_10pct_2013_en WHERE state = '{}' LIMIT 2000".format(state), con=engine)
        temp = temp[temp['message'].str.split().str.len() > 5]
        tweets_2013 = pd.concat([tweets_2013, temp.sample(1000, random_state=42)])
        print(state, len(tweets_2013))
    
    Tweets = pd.concat([tweets_2012, tweets_2013])
    print(len(Tweets))
    return Tweets

def main():
    tweet_df = read_data()
    tweets = tweet_df['message'].tolist()
    states = tweet_df['state'].tolist()
    query_data = zip(tweets, states)
    results = run_baseline(query_data, index=1500)
    

# print(query_GPT("I love my family."))
main()