import asyncio
import os

import momento.aio.simple_cache_client as scc
import momento.errors as errors

from pymongo import MongoClient
import json 
import time
from bson.json_util import dumps, loads

_MOMENTO_AUTH_TOKEN = os.getenv("MOMENTO_AUTH_TOKEN")
_CACHE_NAME = "cache"
_ITEM_DEFAULT_TTL_SECONDS = 60
_KEY = os.getenv("KEY")
_SKIPCACHE = os.getenv("SKIP_CACHE")

client = MongoClient('mongodb+srv://not-my-username:not-my-password@cluster0.oko2ogn.mongodb.net/test')

async def _create_cache(cache_client: scc.SimpleCacheClient, cache_name: str) -> None:
    try:
        await cache_client.create_cache(cache_name)
    except errors.AlreadyExistsError:
        print(f"Cache with name: {cache_name!r} already exists.")


async def _list_caches(cache_client: scc.SimpleCacheClient) -> None:
    print("Listing caches:")
    list_cache_result = await cache_client.list_caches()
    while True:
        for cache_info in list_cache_result.caches():
            print(f"- {cache_info.name()!r}")
        next_token = list_cache_result.next_token()
        if next_token is None:
            break
        list_cache_result = await cache_client.list_caches(next_token)
    print("")

async def main() -> None:
    async with scc.init(_MOMENTO_AUTH_TOKEN, _ITEM_DEFAULT_TTL_SECONDS) as cache_client:
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
                get_resp = await cache_client.get(_CACHE_NAME, _KEY)
                if str(get_resp.status()) == 'CacheGetStatus.HIT':
                    print(f"Look up resulted in a: {str(get_resp.status())}")
                    print(f"Getting Key: {_KEY!r}")
                    get_resp = await cache_client.get(_CACHE_NAME, _KEY)
                    print(f"Looked up Value (cut-off at 100 chars): {get_resp.value()[0:100]!r}")
                else:
                    result = await get_results()
                    json_data = dumps(result) 
                    print(f"Setting Key: {_KEY!r}")
                    await cache_client.set(_CACHE_NAME, _KEY, json_data)
                    print(f"Value stored in Momento (cut-off at 100 chars): {json_data[0:100]!r}")
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