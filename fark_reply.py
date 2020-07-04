import requests
from bs4 import BeautifulSoup
import tweepy
import random
from dotenv import load_dotenv
import os
from urllib3.exceptions import ProtocolError
from urllib.parse import urlparse
from typing import Union

load_dotenv()
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
search_url = "https://www.fark.com/hlsearch"
fark_user_id = "14804898"
vulgar_user_id = "740888554008543232"
response_pool = [
    # "Come argue with farkers in the comment thread",
    "Never leave your basement again with the help of comment thread",
    "It's now news, it's the comment thread",
    "Sure the headline is great, but the real fun is in the comment thread",
    "What else were you going to do today. Visit the comment thread",
    "Tell us what you really think in the comment thread",
    "Here comes the science. And the denial",
    #  "Florida Man",
    # "Let's see what the mods will let us say in the comment thread",
    "Click here for deeply held beliefs",
    "There is a small chance some will say something funny in the comment thread, and a tiny chance they will say something smart",
    "This isn't a thread about beer, but you can make it into one",
    "Because what self respecting farker actually reads the articles",
    "The answer is beer, and talking about beer. Ok maybe whiskey as well",
    "Fark threads are definitely better than twitter threads",
    "You know that urge to step away from the keyboard, ignore it",
    "Click the link. Read the comments. Add your own",
    "Surely nobody could have a problem with this....right",
    "If whiskey is the water of life, then surely... well Fark is alright too I guess",
    "If you were promised that there would be no math, there probably won't be",
    # "If you're reading this on the toilet, we know who you are, and what you've done",
    "The longer you wait, the harder it gets",
    "In every thread in every tab on this site, there is a nobody who dreams of being a somebody. Or at least getting a few funny votes",
    "Work sucks. But farking at work is awesome",
    # "Feel the rythym, feel the rhyme, get on up, it's commenting time",
    "You don't get to 500 comments without making a few enemies",
    "Fark. Where we've been practicing social distancing since before it was popular",
    # "This funny comment thread removed for trolling",
    "Because why should facebook and twitter have all the fun",
    "The only thing better than washing your hands",
    "This comment thread is gold. I was coded to tell the truth. Honest",
    "I take no responsibility for anything in the comment thread",
    "Is it too early to be drunk and farking?",
    "What we've got here in the comments is a failure to communicate",
    "There's no place like the comment thread",
    "Elementary my dear Farker",
    "There's no crying in the comment thread",
    "Proper comment threading? Where we're going, we don't need proper comment threading",
    "Wisdom, Justice, and Moderation. Not just the state motto of Georgia anymore",
    "To the fark bunker. We will be safe there",
    "Squirrel. Fark",
    "A collection of brilliant comments marinated in alcohol",
]


def authorize_tweepy(consumer_key, consumer_secret, access_token, access_secret):
    """
    Sign in to Twitter and gain access to the API
    :param consumer_key:
    :param consumer_secret:
    :param access_token:
    :param access_secret:
    :return:
    """
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)
    return api


def valid_tweet(status):
    """
    Identify if a tweet is posting a link or responding to someone/retweeting/quoting
    A response or retweet or quote will return a False
    :param status: Tweet object
    :return: Boolean
    """
    if (
        status.in_reply_to_status_id
        or status.text.startswith("RT @")
        or hasattr(status, "quoted_status")
    ):
        return False
    else:
        return True


def get_fark_link(url: str) -> Union[str, bool]:
    link = urlparse(url)
    # If the URL points to fark, it is probably a direct link to fark.com/go style
    # and we can take the last 8 digits to get the comment thread link
    if "fark" in link.netloc:
        return f"http://www.fark.com/comments/{url[-8:]}"
    return False


def make_fark_soup(fark_url: str) -> BeautifulSoup:
    """
    Convert the html of the comment thread into a parsed soup output
    :param fark_url: The url to the comments thread
    :return: BeautifulSoup object of the page returned by the Fark search engine
    """
    r = requests.get(fark_url)
    soup = BeautifulSoup(r.text, features="html.parser")
    return soup


def create_tweet_reply(soup: BeautifulSoup) -> str:
    """
    Take the parsed soup of the comment thread. Identify the tag. Return a text response
    :param soup: Soup of the fark comment thread
    :return: Either a random selection, or a special response for Florida or NewsFlash
    """
    fark_tag = [a["title"] for a in soup.select(".commentHeadlineContainerTopic a")]
    if fark_tag[0] == "Florida":
        return "Florida Man thread"
    elif fark_tag[0] == "NewsFlash":
        return "This is a NewsFlash. Please be mindful of that in the thread"
    else:
        return random.choice(response_pool)


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        tweet_id = status.id
        # Step 1: Identify if a tweet is a fark link or not
        if valid_tweet(status):
            # TODO IndexError list index out of range
            # TODO This error happens when a tweet is made without a link. This is often a ModEmail tweet
            # TODO Wrap the if/else in a Try block
            """
            As a remnant from Twitter increasing the tweet length limit, tweets are either extended or original
            The full length urls are stored in different locations for extended/original
            """
            try:
                if "extended_tweet" in status._json:
                    url = status.extended_tweet["entities"]["urls"][0]["expanded_url"]
                else:
                    url = status.entities["urls"][0]["expanded_url"]
            except IndexError:
                return
            # "Convert the fark.com/go link to a link to the comments thread"
            fark_url = get_fark_link(url)
        else:
            return

        # Step 2: Post the response
        soup = make_fark_soup(fark_url)
        fark_response = create_tweet_reply(soup)
        fark_response = f"@fark {fark_response} {fark_url}"
        print(fark_response)
        api.update_status(status=fark_response, in_reply_to_status_id=tweet_id)
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
    # try:
    #     myStream.filter(follow=[fark_user_id], is_async=True)
    # except ProtocolError:
    #     pass
    while True:
        try:
            myStream.filter(follow=[fark_user_id])
        except ProtocolError as e:
            continue
