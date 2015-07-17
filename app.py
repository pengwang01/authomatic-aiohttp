import asyncio
from asyncio import coroutine

from aiohttp import web
from aiohttp_session import get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

import ujson as json
from authomatic import Authomatic

from utils import AioAdapter, login_user, login_required
import config

from pymongo import MongoClient


authomatic = Authomatic(config.OAUTH_CONFIG, str(config.SECRET))
db = None

def insertUser(user_obj):
    print("in insertUser()")
    client = MongoClient()
    db = client.test

    result = db.users.find({"name": user_obj.name})
    if not result:
        result = db.users.insert_one({
                    "name": user_obj.name
                }
            )
        print("new record inserted: ", result.inserted_id)
    else:
        print("record found!")
        for entry in result:
            print(entry)
    

@coroutine
def login(request):
    provider = request.match_info.get('provider', 'fb')
    response = web.Response()
    result = authomatic.login(AioAdapter(request, response), provider)
    if result and result.user:
        response.body = b"User login successfully!"
        result.user.update()
        user_obj = result.user
        print(user_obj)
        #insert user into db
        insertUser(user_obj)
        
        provider_id = "%s:%s" % (provider, user_obj.id)
        email = user_obj.email
        gender = int(user_obj.gender == 'male') # 1 for male and 0 for female
        firstname = user_obj.first_name
        fullname = user_obj.name
        print(provider_id, email, gender, fullname)
        yield from login_user(request, provider_id)
        response.body += bytes(" Hello " + fullname, encoding="UTF-8")
    
    return response


@coroutine
@login_required
def secret(request):
    ''' My awesome login demo '''
    return web.Response(body=b'Some secret')


@coroutine
def init(loop):
    print("In init()")
    app = web.Application(
        # loop=loop,
        middlewares=[session_middleware(EncryptedCookieStorage(config.SECRET))],
    )
    app.router.add_route('GET', '/login/{provider}', login)
    app.router.add_route('GET', '/secret', secret)
    srv = yield from loop.create_server(
        app.make_handler(),
        'auth.tuhao.com',
        8080,
    )
    print("Server started", srv.sockets[0].getsockname())
    return srv

if __name__ == '__main__':
    #create asyncio loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
