-- wrk script: send `depth` requests per write (HTTP/1.1 pipelining), the
-- TechEmpower plaintext convention. Usage: wrk ... -s pipeline.lua URL -- 16
init = function(args)
   local depth = tonumber(args[1]) or 16
   local r = {}
   for i = 1, depth do r[i] = wrk.format() end
   req = table.concat(r)
end
request = function() return req end
