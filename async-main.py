import asyncio
import os

from datetime import timedelta
from momento import CacheClientAsync, Configurations, CredentialProvider
from momento.responses import CacheGet, CacheSet, CreateCache, ListCaches

from pymongo import MongoClient
import json 
import time
from bson.json_util import dumps, loads

# _MOMENTO_AUTH_TOKEN = os.getenv("MOMENTO_AUTH_TOKEN")
_MOMENTO_AUTH_TOKEN = CredentialProvider.from_environment_variable("MOMENTO_AUTH_TOKEN")
_CACHE_NAME = "cache"
_ITEM_DEFAULT_TTL_SECONDS = timedelta(seconds=60)
_KEY = os.getenv("KEY")
_SKIPCACHE = os.getenv("SKIP_CACHE")

client = MongoClient('mongodb+srv://not-my-username:not-my-password@cluster0.oko2ogn.mongodb.net/test')

async def _create_cache(cache_client: CacheClientAsync, cache_name: str) -> None:
    try:
        await cache_client.create_cache(cache_name)
    except CreateCache.CacheAlreadyExists():
        print(f"Cache with name: {cache_name!r} already exists.")

async def _list_caches(cache_client: CacheClientAsync) -> None:
    print("Listing caches:")
    list_caches_response = await cache_client.list_caches()
    print (list_caches_response)
    print("")

async def main() -> None:
    async with await CacheClientAsync.create(Configurations.Laptop.v1(), _MOMENTO_AUTH_TOKEN, _ITEM_DEFAULT_TTL_SECONDS) as cache_client:
        await _create_cache(cache_client, _CACHE_NAME)
        await _list_caches(cache_client)
        skip_cache = _SKIPCACHE=="True"
        results_dict = {}
        
        for x in range(10):
            print(f"Attempt {x+1!r}")
            loopStartTime = time.time()
            if (skip_cache):
                result = await get_results()
                json_data = dumps(result) 
                print(f"Uncached item (cut-off at 100 chars): {json_data[0:100]!r}")
            else:
                get_response = await cache_client.get(_CACHE_NAME, _KEY)
                match get_response:
                    case CacheGet.Hit() as hit:
                        print(f"Look up resulted in a: {hit}")
                        print(f"Getting Key: {_KEY!r}")
                        print(f"Looked up Value (cut-off at 100 chars): {hit}")
                    case CacheGet.Miss():
                        # print("Look up resulted in a: miss. This is unexpected.")
                        result = await get_results()
                        json_data = dumps(result) 
                        print(f"Setting Key: {_KEY!r}")
                        await cache_client.set(_CACHE_NAME, _KEY, json_data)
                        print(f"Value stored in Momento (cut-off at 100 chars): {json_data[0:100]!r}")
                    case CacheGet.Error() as error:
                        print(f"Error getting cache: {error.message}")
                    case _:
                        print("Unreachable")
            executionTime = (time.time() - loopStartTime)
            results_dict[x] = executionTime
        # finally
        await get_avg_results(results_dict)

async def get_results():
    result = client['sample_analytics']['transactions'].aggregate([
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
    return result

async def get_avg_results(_result_dict):
    etime = 0
    for i in _result_dict.values():
        etime += i
    return print(f'Average execution time in seconds: {etime/len(_result_dict)!r}')
    
if __name__ == "__main__":
    programStartTime = time.time()
    asyncio.run(main())
    totalExecutionTime = (time.time() - programStartTime)
    print(f'Total execution time in seconds: {totalExecutionTime!r}')