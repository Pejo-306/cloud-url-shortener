"""Check that a Redis 8.2 is running on your local machine

Connection details:
- redis: 127.0.0.1:6379
- redisinsight: 127.0.0.1:5540

Expect to see the string "Redis 8.2" pritned in your local console.

You can also access the Redis Insight UI at localhost:5540 and confirm the
string 'framework' is set.
"""

import redis


def main():
    r = redis.Redis(host='localhost', port=6379, db=0)

    r.set('framework', 'Redis 8.2')
    print(r.get('framework').decode())


if __name__ == '__main__':
    main()
