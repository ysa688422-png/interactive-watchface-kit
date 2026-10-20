-- Independent host-side test doubles. These do not emulate the watch hardware.
local M = {}

function M.new(options)
    options = options or {}
    local state = {now = 0, objects = {}, timers = {}, subscriptions = {}, values = {}, calls = {}}
    local methods = {}
    local function create(kind, parent, props)
        local obj = setmetatable({kind = kind, props = {}, flags = {}, children = {}, parent = parent}, {__index = methods})
        state.objects[#state.objects + 1] = obj
        if parent then parent.children[#parent.children + 1] = obj end
        obj:set(props or {})
        return obj
    end
    function methods:set(props)
        for k, v in pairs(props) do self.props[k] = v end
        return self
    end
    function methods:add_flag(flag) self.flags[flag] = true; return self end
    function methods:clear_flag(flag) self.flags[flag] = nil; return self end
    function methods:onClicked(cb) self.clicked = cb; return self end
    function methods:onPressed(cb) self.pressed = cb; return self end
    function methods:delete() self.deleted = true end
    function methods:invalidate() end
    function methods:is_visible() return not self.flags.HIDDEN and not self.props.hidden and not self.deleted end
    function methods:get_img_size() return self.props.w or 336, self.props.h or 480 end
    function methods:get_parent() return self.parent end
    function methods:get_child_cnt() return #self.children end
    for _, kind in ipairs({"Object", "Image", "Label", "Line", "Button"}) do
        methods[kind] = function(self, props) return create(kind, self, props) end
    end

    local lvgl = {
        FLAG = {SCROLLABLE = "SCROLLABLE", CLICKABLE = "CLICKABLE", EVENT_BUBBLE = "EVENT_BUBBLE", HIDDEN = "HIDDEN"},
        ALIGN = {CENTER = "CENTER", TOP_LEFT = "TOP_LEFT", TOP_MID = "TOP_MID", TOP_RIGHT = "TOP_RIGHT", BOTTOM_LEFT = "BOTTOM_LEFT", BOTTOM_MID = "BOTTOM_MID", BOTTOM_RIGHT = "BOTTOM_RIGHT", LEFT_MID = "LEFT_MID", RIGHT_MID = "RIGHT_MID"},
        LABEL = {LONG_CLIP = "LONG_CLIP", LONG_SCROLL_CIRCULAR = "LONG_SCROLL_CIRCULAR", LONG_DOT = "LONG_DOT"},
        BUILTIN_FONT = {MONTSERRAT_20 = "MONTSERRAT_20", MONTSERRAT_16 = "MONTSERRAT_16"},
        SIZE_CONTENT = -1,
        OPA = function(value) return math.floor(value * 255 / 100) end,
        HOR_RES = function() return 336 end,
        VER_RES = function() return 480 end,
        tick_get = function() return state.now end,
        Font = function(name, size) return {name = name, size = size} end,
    }
    for _, kind in ipairs({"Object", "Image", "Label", "Line", "Button"}) do
        lvgl[kind] = function(parent, props) return create(kind, parent, props) end
    end
    function lvgl.Timer(opts)
        local timer = {period = 0, repeat_count = -1, paused = true, deleted = false, calls = 0}
        function timer:set(values)
            for k, v in pairs(values) do self[k] = v end
            self.next = state.now + self.period
            if self.period == 0 then self.paused = true end
            return self
        end
        function timer:pause() self.paused = true end
        function timer:resume() self.paused = false; self.next = state.now + self.period end
        function timer:ready() self.next = state.now end
        function timer:delete() self.deleted = true; self.paused = true end
        timer:set(opts or {})
        if opts and opts.paused == nil and timer.period > 0 then timer.paused = false end
        state.timers[#state.timers + 1] = timer
        return timer
    end
    local dataman = {}
    function dataman.subscribe(key, obj, cb)
        assert(type(key) == "string" and type(cb) == "function", "invalid dataman subscription")
        if options.reject_keys and options.reject_keys[key] then error("unsupported data key: " .. key) end
        local sub = {key = key, obj = obj, cb = cb, paused = false}
        state.subscriptions[#state.subscriptions + 1] = sub
        if options.initial_values and options.initial_values[key] ~= nil then
            state.values[key] = options.initial_values[key]
            cb(obj, state.values[key])
        end
        return sub
    end
    function dataman.pause(token) token.paused = true end
    function dataman.resume(token)
        token.paused = false
        if options.replay_on_resume and state.values[token.key] ~= nil then
            token.cb(token.obj, state.values[token.key])
        end
    end
    function state:publish(key, value)
        self.values[key] = value
        for _, sub in ipairs(self.subscriptions) do
            if sub.key == key and not sub.paused then sub.cb(sub.obj, value) end
        end
    end
    function state:advance(delta)
        assert(delta >= 0)
        local limit, fires = self.now + delta, 0
        while true do
            local next_timer
            for _, timer in ipairs(self.timers) do
                if not timer.paused and not timer.deleted and timer.next <= limit and
                    (not next_timer or timer.next < next_timer.next) then next_timer = timer end
            end
            if not next_timer then break end
            self.now = next_timer.next
            fires = fires + 1
            assert(fires < 20000, "timer callback loop did not terminate")
            next_timer.calls = next_timer.calls + 1
            next_timer.next = self.now + next_timer.period
            if next_timer.repeat_count > 0 then
                next_timer.repeat_count = next_timer.repeat_count - 1
                if next_timer.repeat_count == 0 then next_timer.paused = true end
            end
            next_timer.cb(next_timer)
        end
        self.now = limit
        return fires
    end
    function state:click(obj)
        assert(obj.clicked, "object has no click callback")
        obj.clicked(obj)
    end
    function state:find(predicate)
        local result = {}
        for _, obj in ipairs(self.objects) do if predicate(obj) then result[#result + 1] = obj end end
        return result
    end
    function state:snapshot()
        local data = {}
        for i, obj in ipairs(self.objects) do
            data[#data + 1] = {index = i, kind = obj.kind, text = obj.props.text, src = obj.props.src,
                hidden = not obj:is_visible(), x = obj.props.x, y = obj.props.y, clickable = obj.clicked ~= nil}
        end
        return data
    end
    function state:install()
        package.loaded.lvgl, package.loaded.dataman = lvgl, dataman
        package.preload.lvgl = function() return lvgl end
        package.preload.dataman = function() return dataman end
        _G.SCRIPT_PATH = "stub://watch/"
        _G.ScreenStateChangedCB = nil
    end
    state.lvgl, state.dataman = lvgl, dataman
    return state
end
return M
