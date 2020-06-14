from redis import Redis
from rq import Queue
from fark_reply import connect_to_twitter, print_tweet, MyStreamListener


q = Queue(connection=Redis())

connect_to_twitter()

result = q.enqueue(print, MyStreamListener.tweet_status())