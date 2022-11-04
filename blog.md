## Introduction

As a new entrance in the marketplace as Cache-as-a-Service, they've asked me to evaluate their technology and write up about it. I'm coming in with an open-mind as an Amazon Web Service (AWS) Data Hero. I'm partial to AWS ElasticSearch Redis as my go-to caching provider, however with Momento in the picture, I've been inclined to check them out and see how much faster, cheaper, and better(?) they are. Out of the bat, I can argue that they require far less ceremony for you to set up caching. One thing I'd like to see is having the same API as Redis or Memcached so businesses can move their code over without any or minimal changes -- other than configs, of course.

For some of you, it might be a problem with yet-another-vendor to work with however, studies repeatedly shows a 2-second wait on a website could potentially drive customers elsewhere. This is the kind of study that keeps marketing managers awake at night and pushes dev teams to innovate further. If the software part is exhausted, they resort to put their databases closer to their customers. When the databases are optimized to the hilt, then they'll put caching in front of it. However, websites are increasing in complexity while your browser engines are working hard getting indauntated with videos, graphics, and ads tracking tools. There'll always be some optimization that's going on whenever a new technology or tooling enters the picture.

Since major cloud providers have so many other things on their proverbial plate, Momento specializes in one thing only, caching and reducing latency as much as possible. Although it is a cloud-based provider, it has a presence across all clouds and their respective edge locations thus the latency behind caching will be reduced to the bare minimum. This is a game-changer for those who may have an on-premise service, but could not move to the cloud yet, or for those enterprises that wants to be risk-adverse thus cloud-agnostic, or there might be players who doesn't want to subscribe to a service 

## Typical client-server setup

If I was building out a website that has a low risk of turnover such as a personal blog or a website that caters to a niche, I would just run everything on AWS. If I was advising a client who visibily sweats at the prospect of having a single-tenancy risk, and that their website requires infinite uptime with extremely low latency, I would advise spreading out the pain onto multiple vendors while having a fail-fail-fail-over (not a typo!) to one cloud provider.

Most websites nowadays are built using the MACH architecture (Microservices, API, Cloud-native, and Headless). Microservices are little programs that does one, ok, maybe two things. APIs are URI endpoints that we interact with. Cloud-native means it can run anywhere -- cloud, on-prem, hybrid, and Headless means it can be run programmatically or have a UI-based front-end built in front of the API -- clients would either roll their own, use open source tools, or purchase a third-party provider.

Now armed with this level of detail, let's come up with a hypothetical website and what tools it'd be running off. On AWS, typically, I would have a running website hosted using Amplify, DocumentDB (compatible with MongoDB), Lambda, and API Gateway. Any website request would first go through the API Gateway endpoint, then passed off to a Lambda which consumes the request and determines what the request is asking for. The Lambda would then query the DocumentDB, wait for the data to come back, and when it does, it generates a packaged response (JSON) that gets passed back through the API Gateway as a HTTP response to the Amplify web app. Let's go with that thinking the rest of the way and figure out how we can be more risk-adverse and cloud-agnostic.

## Taking action 

As a business person, I want to ensure my systems are running as optimized as possible without any major outages. In the cloud, I could create an active-active setup, however it is very costly and databases outside of AWS DynamoDB doesn't have the ability for seamless transition from one cloud region to another. The technology teams are required to intervene and manually change configurations so their apps are pointing to a different region.

## Database

As mentioned, we're using DocumentDB as our transactional store. While DocumentDB can hold its own in terms of failover, latency, and extreme durability; there is a business need to alleviate some risks by farming it out to a third-party provider. Because the DocumentDB API is 100% compatible with current versions of MongoDB, we can migrate our databases over to a specialized cloud data provider, MongoDB Atlas. Atlas has a cool ability to fail over in multiple regions AND to multiple cloud providers. If Google Cloud goes down, MongoDB will fail the database over to AWS or Azure. We can use MongoDB as our transactional data store and then we can sleep at night knowing the failovers will work as promised and the risks passed onto the team at MongoDB.

I've put together a cloud-based database that isn't tied into a particular cloud provider, and compared results with a caching service that again isn't tied to a particiular cloud provider. First, let's check out the logic.

I want to see how much time I'm saving by using Momento to retrieve, say, a complicated data set from MongoDB from my laptop which is behind a 100Mb/sec internet connection. First, I would sign up for a free MongoDB Atlas account using my Github credentials. You can go to https://cloud.mongodb.com and start the set up. It's free; no credit cards required. MongoDB gratiously provides a series of collections (databases) that you can use to query against. I've been looking for some data that would return something that requires some aggregation and would take time to retrieve. 

I've settled into returning data from the sample_analytics collection pulling information from the transactions table using a simple group looking for transactions buying a specific stock. Note: if you feel it's not complicated enough, feel free to DM me on Twitter or LinkedIn!

```json
['sample_analytics']['transactions'].aggregate([
            {
                '$unwind': {
                    'path': '$transactions'
                }
            }, {
                '$match': {
                    '$and': [
                        {
                            'transactions.transaction_code': 'buy', 
                            'transactions.symbol': 'adbe'
                        }
                    ]
                }
            }, {
                '$group': {
                    '_id': '$_id', 
                    'transaction_item': {
                        '$push': '$transactions'
                    }
                }
            }
        ])
```

By the way, if you're wondering why your MongoDB program may not be working for you, you might need to go to Security > Network Access in Atlas to allow the IP you're located at to access the database. I've gotten caught many times missing that since I switch locations and computers so often that I lost count.

Once it works in the MongoDB UI and in your Python program using the pymongo library, then we can proceed to set up Momento. Momento set up is very easy. If you disagree, let me know as I don't know of any service that lets you run anything new that only requires 4 to 5 lines of commands depnding on your operating system. Using your email as the username, you can follow along the 'Getting Started' page to get the Momento CLI installed on your machine. After that, your momento account can be up and running in literally seconds.

Next, is getting Python to work with Momento. You can pull a program from their github repo and start using it testing creation of a key-value and then reading it. Take note that you'll need to use your authentication token that Momento emailed you during setup. You can use Momento as a simple database if you're so inclined, but you'll need to seed it every time the entry expires. That's why we have databases like MongoDB to store data in a more persistent and robsut way.

After testing Momento using your Python program, it is time to combine the two access patterns into one. We need to decide on a approach to retrieve the data assuming cached data is quicker. Well, it has to be since your database is sweating CPU cycles trying to aggregate the data in the fly while the cache service only does a key lookup and returns one simple value.

Assume we have a service that allows the user to see recent trades by company employees. Some companies are so heavily-regulated that all stock trades are monitored to avoid the perspective of insider trading as the company may be providing news. The data will be updated but not very often thus we can assume the data would not go stale quickly. 

## Running Python

Using the program I've put together with the SKIP_CACHE flag of True, consistently, it takes about 5 seconds to retrieve the same record 10 times from MongoDB.

```bash
$ DEBUG=true MOMENTO_AUTH_TOKEN=this-is-a-long-hash-token-it-doesnt-work-so-dont-try KEY=KEY1 SKIP_CACHE=True python3 async-main.py
```

Using my slow internet speed -- 10 times at 5 seconds. That's an average of 0.5 seconds per data retrival. Don't forget we'd need to render the data coming back into a web page using CSS, JavaScript, and depending on the speed of the browser engine, your internet speed, your desktop computer speed, and of course the servers' network latency and bandwidth... tons of bottlenecks to worry about thus overall it'll take longer than 0.5 seconds to present the data on your web page. I can tell you we can the data retieval much quicker. 

## New code sequence

We need to figure out the sequence of how we retrieve data working with a caching service:

1. User logs onto website
2. User looks up a ticker symbol
3. Program looks at Momento first to see if ticker has been saved in cache. We can probably have a cache name using the pattern as "<tickername>-<transactiontype>", or using real examples: adbe-buy, amzn-sell, msft-sell, goog-buy. This would be our Momento cache key.
4. If the key isn't found in Momento, retrieve from MongoDB Atlas.
    a. After pull data from MongoDB Atlas, save to Momento.
5. If stored in Momento, return results to user.

```bash
$ DEBUG=true MOMENTO_AUTH_TOKEN=this-is-a-long-hash-token-it-doesnt-work-so-dont-try KEY=KEY1 SKIP_CACHE=False python3 async-main.py
```

In the first go around, it saves the key in Momento then we retrive it over and over 9 more times. I see it took a little over 3 seconds to do.

Second time, it retrieves 100% of data from Momento only, and I've see it go under 3 seconds. If we average it up to 3 seconds, that'd be .3 of second per request! A 40% reduction in processing time from the data side.

## Github repository

I've written this logic in my Python program here in the github repo at async-main.py. Please give it a shot and report back if you feel my numbers were a bit off kilter.

## Conclusion 

While the cloud hyperscaler offerings are great and robust too, there are always configuration and security concerns to manage. You need to figure out what network traffic is being expected and needing to tune your caching service to match expected traffic surges. What if the unexpected happens either way? You could be losing money if you scale the caching service too much for a low traffic period, or potentially lose customers because the website is taking too long to load the data. 

Momento aims to minimize the need to manage or scale the cache service making it easy for you to focus on more important things, like your technical debts! Some folks might even NOT be in the cloud thus Momento can be a great alternative minimizing the need to slam your on-prem databases and causing your transaction logs from blowing up and saturating your disk space -- I know every DBAs deal with far too often.

I have received no compenstation for writing this article save for making great connections with the Momento team and showing that I believe in their mission to #CacheTheWorld. There's some great people on that team and I strongly encourage you to reach out to them if you currently have some costs or latency concerns with your current solution.

## Python Notes

I'm using Python as it's pretty much a universal language used by many data oriented shops and it's easy to understand as you step through the logic. When I started writing this blog, I used Python 3.9, but during this final push, I've decided to use Python 3.11. I can tell you right out of the bat it tells me right away what the error is without being cryptic. For example, when I start the program, we need to add an Authentication Token variable so Momento can validate that the HTTP request is authenticated. 

```bash
$ python async-main.py
```
returns
```
...
  File "/Users/rob.koch/Library/Python/3.11/lib/python/site-packages/momento/_momento_endpoint_resolver.py", line 26, in resolve
    return _getEndpointFromToken(auth_token)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/rob.koch/Library/Python/3.11/lib/python/site-packages/momento/_momento_endpoint_resolver.py", line 37, in _getEndpointFromToken
    raise errors.InvalidArgumentError("Invalid Auth token.") from None
momento.errors.InvalidArgumentError: Invalid Auth token.
```

Just from running this command, I immediately knew what the issue was and had to run the command passing in the auth token variable like such:
```bash
$ DEBUG=true MOMENTO_AUTH_TOKEN=this-is-a-long-hash-token-it-doesnt-work-so-dont-try python3 async-main.py
```

As I always forget to do the little things, I want something to help me remember faster. Enough gushing over Python 3.11.