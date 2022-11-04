from pymongo import MongoClient
import json 
import time

startTime = time.time()

# Requires the PyMongo package.
# https://api.mongodb.com/python/current

client = MongoClient('mongodb+srv://momentomongo:not-my-password@cluster0.oko2ogn.mongodb.net/test')
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
print(result)
for i in result:
    print(i)

executionTime = (time.time() - startTime)
print('Execution time in seconds: ' + str(executionTime))
