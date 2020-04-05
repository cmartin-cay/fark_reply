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
    "If you're reading this on the toilet, we know who you are, and what you've done",
    "The longer you wait, the harder it gets",
    "In every thread in every tab on this site, there is a nobody who dreams of being a somebody. Or at least getting a few funny votes",
    "Work sucks. But farking at work is awesome",
    "Feel the rythym, feel the rhyme, get on up, it's commenting time",
    "You don't get to 500 comments without making a few enemies",
    "Fark. Where we've been practicing social distancing since before it was popular",
    "This funny comment thread removed for trolling",
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
    "Wisdom, Justice, and Moderation. Not just the state motto of Georgia anymore"
]


def create_payload(search_term: str) -> dict:
    """
    Creates a payload item for use in a reauest object
    :param search_term: A string generated from a twitter status
    :return: A dictionary formatted for the Fark search tool
    """
    return {"qq": search_term, "o": 0}


def get_relevancy_score(soup: BeautifulSoup) -> int:
    """
    Searches the Fark soup and return the relevancy score of the first result
    :param soup: Fark website converted to BS4 soup
    :return: A relevancy score
    """
    revelancy = soup.find("span", attrs={"style": {"font-size:smaller"}})
    # returns "(score xxx%)"
    # so slice the string to just get the % then convert to int
    return int(revelancy.text[7:-2])


def create_tweet_reply(soup: BeautifulSoup) -> str:
    fark_tag = [a["title"] for a in soup.select(".headlineTopic a")]
    if fark_tag[0] == "Florida":
        return "Florida Man thread"
    else:
        return random.choice(response_pool)


def make_fark_soup(search_term: str) -> BeautifulSoup:
    """

    :param search_term: The string you want to search in the Fark search engine
    :return: BeautifulSoup object of the page returned by the Fark search engine
    """
    if not search_term:
        return None
    r = requests.get(search_url, create_payload(search_term))
    soup = BeautifulSoup(r.text, features="html.parser")
    return soup


def get_fark_comment_link(soup: BeautifulSoup) -> str:
    """
    Parses the fark website soup to return the url of the first comment thread
    :param soup: Fark website converted to BS4 soup
    :return: URL of the first comment thread
    """
    # Check to see if any results were found
    comment_threads = soup.findAll("div", {"class": "icon_comment_container"})
    if len(comment_threads) == 0:
        return None
    # Once we know there are results, identify all the links to the comment threads
    comment_thread_links = [a["href"] for a in soup.select(".icon_comment_container a[href]")]
    return comment_thread_links[0]


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


def tweet_text(status, text):
    """
    Take a tweet object, and the already established text of the tweet and returns
    None or the cleaned text
    :param status: Twitter status object
    :param text: Previously established text of the tweet
    :return: None or Cleaned text suitable for passing to the Fark search page
    """
    if (
            status.in_reply_to_status_id
            or text.startswith("RT @")
            or hasattr(status, "quoted_status")
    ):
        print(text)
        print("Probably a reply or a retweet")
        print("______________________________")
        return None
    # Strip out http references at the end of the tweet
    # Unfortunately this will remove all http links - this can be worked on
    text = re.sub(r"http\S+", "", text).rstrip()
    return text


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
        text = tweet_text(status, text)
        # TODO Identify if tweet is a News Flash and process that in a slightly different way

        # If the tweet isn't relevant, just stop right here
        if not text:
            return
        print(f"Step 2 {text}, {tweet_id}")
        print("____________________________")
        # Step 3: Post the response
        fark_soup = make_fark_soup(text)
        if fark_soup:
            fark_url = get_fark_comment_link(fark_soup)
            relevancy_score = get_relevancy_score(fark_soup)
            if fark_url and relevancy_score > 75:
                fark_response = create_tweet_reply(fark_soup)
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
    # while True:
    #     try:
    #         myStream.filter(follow=[fark_user_id], is_async=True)
    #     except ProtocolError:
    #         continue
    try:
        myStream.filter(follow=[fark_user_id], is_async=True)
    except Exception as e:
        pass
