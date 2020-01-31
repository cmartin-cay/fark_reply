import requests
from bs4 import BeautifulSoup
import tweepy
import re
import random
from dotenv import load_dotenv
import os
from urllib3.exceptions import ProtocolError
import time


load_dotenv()
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
search_url = "https://www.fark.com/hlsearch"
fark_user_id = "14804898"
response_pool = [
    "Come argue with farkers in the comment thread",
    "Never leave your basement again with the help of comment thread",
    "It's now news, it's the comment thread",
    "Sure the headline is great, but the real fun is in the comment thread",
    "What else were you going to do today. Visit the comment thread",
    "Tell us what you really think in the comment thread",
    "Here comes the science. And the denial",
    #  "Florida Man",
    "Let's see what the mods will let us say in the comment thread",
    "Click here for deeply held beliefs",
    "There is a small chance some will say something funny in the comment thread, and a tiny chance they will say something smart",
    "This isn't a thread about beer, but you can make it into one",
    "Because what self respecting farker actually reads the articles",
]


def create_payload(search_term):
    return {"qq": search_term, "o": 0}


def get_relevant(soup):
    revelancy = soup.find("span", attrs={"style": {"font-size:smaller"}})
    # returns "(score xxx%)"
    # so slice the string to just get the % then convert to int
    return int(revelancy.text[7:-2])


def create_tweet_reply(fark_tag):
    if fark_tag == "Florida":
        return "Florida Man thread"
    elif fark_tag == "NewsFlash":
        return "NewsFlash thread. Please be responsible"
    else:
        return random.choice(response_pool)


def get_fark_response(search_term):
    if not search_term:
        return None
    r = requests.get(search_url, create_payload(search_term))
    soup = BeautifulSoup(r.text, features="html.parser")
    mydivs = soup.findAll("div", {"class": "icon_comment_container"})
    if len(mydivs) == 0:
        return None
    if get_relevant(soup) < 75:
        print(f"Relevancy score: <75%")
        return None
    fark_tag = [a["title"] for a in soup.select(".headlineTopic a")]
    tweet_reply_text = create_tweet_reply(fark_tag[0])
    res = [a["href"] for a in soup.select(".icon_comment_container a[href]")]
    return (res[0], tweet_reply_text)


# Set up the Tweepy API
def authorize_tweepy(consumer_key, consumer_secret, access_token, access_secret):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)
    return api


def tweet_text(tweet):
    if (
        tweet.in_reply_to_status_id
        or tweet.full_text.startswith("RT @")
        or tweet.quoted_status
    ):
        return None
    text = tweet.full_text
    # Strip out http references at the end of the tweet
    # Unfortunately this will remove all http links - this can be worked on
    text = re.sub(r"http\S+", "", text).rstrip()
    return (text, tweet.id)


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        tweet_id = status.id
        # Step 1: Get the text of the tweet - either normal or extended
        if "extended_tweet" in status._json:
            text = status.extended_tweet["full_text"]
        else:
            text = status.text
        # Step 2: Identify if it is a relevant tweet
        # If relevant, strip out the http link and return the search string and tweet id
        if (
            status.in_reply_to_status_id
            or text.startswith("RT @")
            or hasattr(status, "quoted_status")
        ):
            print(text)
            print("Probably a reply or a retweet")
            print("______________________________")
            return None
        text = re.sub(r"http\S+", "", text).rstrip()
        # Step 3: Post the response
        print(text, tweet_id)
        fark_url = get_fark_response(text)
        if not fark_url:
            return None
        fark_url, tweet_response = fark_url
        fark_url = f"@fark {tweet_response} {fark_url}"
        print(fark_url)
        api.update_status(status=fark_url, in_reply_to_status_id=tweet_id)
        print("Response posted")
        print("____________________________")

    def on_disconnect(self, notice):
        print(f"Disconnect by {notice}")

    def on_exception(self, exception):
        print(exception)
        return

    # def keep_alive(self):
    #     print("__________________________")
    #     print("Keep Alive Call Received")
    #     print("___________________________")

    def on_connect(self):
        print("Connected to the Stream")


if __name__ == "__main__":
    api = authorize_tweepy(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(
        auth=api.auth, listener=myStreamListener, tweet_mode="extended"
    )
    # while True:
    #     try:
    #         myStream.filter(follow=[fark_user_id], is_async=True)
    #     except ProtocolError:
    #         continue
    try:
        myStream.filter(follow=[fark_user_id], is_async=True)
    except Exception as e:
        pass
