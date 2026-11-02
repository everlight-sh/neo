-- wrk script: POST /nbody with a small JSON body
wrk.method = "POST"
wrk.body = '{"n":256,"steps":4}'
wrk.headers["Content-Type"] = "application/json"
