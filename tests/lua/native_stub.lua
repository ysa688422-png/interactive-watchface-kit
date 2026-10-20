-- Extend the existing independent host doubles with subscription teardown.
-- This executes Lua logic; it is not firmware, rendering, Bluetooth or sensor emulation.
local base = dofile("tests/lua/base_stub.lua")
local M = {}
function M.new(options)
    options = options or {}
    local state = base.new(options)
    -- Record attempted targets before a deliberately rejected subscription.
    -- Tests can identify semantic labels without binding to their coordinates.
    state.subscriptionTargets = {}
    local originalSubscribe = state.dataman.subscribe
    function state.dataman.subscribe(key, object, callback)
        state.subscriptionTargets[key] = object
        return originalSubscribe(key, object, callback)
    end
    state.unsubscribeCalls = 0
    function state.dataman.unsubscribe(token)
        assert(type(token) == "table", "unsubscribe requires a subscription token")
        if not token.unsubscribed then state.unsubscribeCalls = state.unsubscribeCalls + 1 end
        token.unsubscribed, token.paused = true, true
    end
    if options.no_unsubscribe then state.dataman.unsubscribe = nil end
    if options.no_pause_resume then state.dataman.pause, state.dataman.resume = nil, nil end
    return state
end
return M
