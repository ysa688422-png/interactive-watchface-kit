-- Interactive Watchface Kit: n67 / 336x480.
-- Reads latest band data; never controls the sensor or performs network I/O.
local lvgl = require("lvgl")
local dataman = require("dataman")
local basePath = SCRIPT_PATH
local HEART_RATE_THRESHOLD = 120
local assetGeometry = {} -- ASSET_GEOMETRY
local values, tokens, fonts, chineseFonts = {}, {}, {}, {}
local state = {
    active = true, initializing = true, resuming = false, destroyed = false,
    phase = "idle", form = "human", emotion = "neutral", closed = false,
    heldFlower = false, backdrop = "lavender",
    elapsed = 0, running = false, origin = "idle", highLatched = false,
    triggerCount = 0, autoTriggerCount = 0, manualTriggerCount = 0,
    transientTimer = nil, idleTimer = nil, idleCursor = 1, epoch = 0,
    personSrc = "", log = {},
}

local function record(event)
    state.log[#state.log + 1] = { event = event, elapsed = state.elapsed, phase = state.phase }
    if #state.log > 32 then table.remove(state.log, 1) end
end
local function font(size)
    if fonts[size] then return fonts[size] end
    for _, name in ipairs({ "MiSans-Medium", "MiSans-Demibold", "misansw_demibold", "MiSans-Regular" }) do
        local ok, result = pcall(lvgl.Font, name, size)
        if ok and result then
            fonts[size], chineseFonts[size] = result, true
            return result
        end
    end
    fonts[size] = lvgl.BUILTIN_FONT and lvgl.BUILTIN_FONT.MONTSERRAT_20
    chineseFonts[size] = false
    return fonts[size]
end
local root = lvgl.Object(nil, {
    w = lvgl.HOR_RES(), h = lvgl.VER_RES(),
    bg_color = 0x000000, bg_opa = 255, border_width = 0, pad_all = 0,
})
root:clear_flag(lvgl.FLAG.SCROLLABLE)
root:add_flag(lvgl.FLAG.EVENT_BUBBLE)
local face = lvgl.Object(root, {
    w = 336, h = 480, align = lvgl.ALIGN.CENTER,
    bg_opa = 0, border_width = 0, pad_all = 0,
})
face:clear_flag(lvgl.FLAG.SCROLLABLE)
face:add_flag(lvgl.FLAG.EVENT_BUBBLE)
local function inert(obj)
    obj:clear_flag(lvgl.FLAG.SCROLLABLE)
    obj:clear_flag(lvgl.FLAG.CLICKABLE)
    obj:add_flag(lvgl.FLAG.EVENT_BUBBLE)
    return obj
end
local function image(name, opacity)
    local geometry = assetGeometry[name] or {}
    return inert(lvgl.Image(face, { x = geometry.x or 0, y = geometry.y or 0,
        src = basePath .. name .. ".bin", opa = opacity }))
end
local lavender = image("background-lavender", 255)
local fireworks1 = image("fireworks-1", 0)
local fireworks2 = image("fireworks-2", 0)
-- Attenuate the fireworks only. Character and blast art always paint above this.
local backgroundShade = image("ui-background-shade", 0)
local person = image("human-neutral-open", 255)
state.personSrc = "human-neutral-open"
local cover = inert(lvgl.Object(face, {
    x = 0, y = 0, w = 336, h = 432,
    bg_color = 0x342C2A, bg_opa = 0, border_width = 0, pad_all = 0,
}))
local smoke = image("smoke", 0)
local flash = image("flash", 0)
local lavenderFooter = image("footer-lavender", 255)
local blackFooter = image("footer-black", 0)
local function label(x, y, w, h, size, value, color)
    return inert(lvgl.Label(face, {
        x = x, y = y, w = w, h = h, text = value,
        text_font = font(size), font_size = size, text_color = color or 0x34233F,
        text_align = lvgl.ALIGN.TOP_MID, long_mode = lvgl.LABEL.LONG_CLIP,
        bg_opa = 0, border_width = 0, pad_all = 0,
    }))
end
local DATE_SIZE = 18
local timeLabel = label(16, 12, 128, 58, 48, "--:--")
local dateLabel = label(16, 70, 128, 26, DATE_SIZE, "--")
local stepLabel = label(20, 420, 160, 38, 32, "--")
local heartLabel = label(218, 416, 98, 42, 36, "--")
local stepIcon = image("icon-steps-light", 255)
local heartIcon = image("icon-heart-light", 255)
local batteryBody = inert(lvgl.Object(face, {
    x = 280, y = 30, w = 30, h = 14, radius = 3,
    bg_opa = 0, border_color = 0x34233F, border_opa = 255, border_width = 1, pad_all = 0,
}))
local batteryTerminal = inert(lvgl.Object(face, {
    x = 310, y = 34, w = 2, h = 6, radius = 1,
    bg_color = 0x34233F, bg_opa = 255, border_width = 0, pad_all = 0,
}))
local batteryFill = inert(lvgl.Object(face, {
    x = 283, y = 33, w = 1, h = 8, radius = 1,
    bg_color = 0x34233F, bg_opa = 255, opa = 0, border_width = 0, pad_all = 0,
}))
local batteryUnknown = inert(lvgl.Object(face, {
    x = 290, y = 36, w = 10, h = 2, radius = 1,
    bg_color = 0x34233F, bg_opa = 255, opa = 255, border_width = 0, pad_all = 0,
}))
local propsCache = {}
local function set(obj, key, value)
    local cache = propsCache[obj]
    if not cache then cache = {}; propsCache[obj] = cache end
    if cache[key] ~= value then obj:set { [key] = value }; cache[key] = value end
end
local function opacity(obj, value)
    set(obj, "opa", math.floor(math.max(0, math.min(255, value)) + 0.5))
end
local function renderBattery()
    local value = values.battery
    set(batteryFill, "w", value ~= nil and math.max(1, math.floor(24 * value / 100 + 0.5)) or 1)
    opacity(batteryFill, value ~= nil and value > 0 and 255 or 0)
    opacity(batteryUnknown, value == nil and 255 or 0)
end
local function setBackdrop(black)
    state.backdrop = black and "black" or "lavender"
    opacity(lavender, black and 0 or 255)
    opacity(lavenderFooter, black and 0 or 255)
    opacity(blackFooter, black and 255 or 0)
    opacity(backgroundShade, black and 255 or 0)
    for _, obj in ipairs({ timeLabel, dateLabel, stepLabel, heartLabel }) do
        set(obj, "text_color", black and 0xFFFFFF or 0x34233F)
    end
    local suffix = black and "dark" or "light"
    set(stepIcon, "src", basePath .. "icon-steps-" .. suffix .. ".bin")
    set(heartIcon, "src", basePath .. "icon-heart-" .. suffix .. ".bin")
    set(batteryBody, "border_color", black and 0xFFFFFF or 0x34233F)
    for _, obj in ipairs({ batteryTerminal, batteryFill, batteryUnknown }) do
        set(obj, "bg_color", black and 0xFFFFFF or 0x34233F)
    end
end
local function setPerson(name)
    if state.personSrc ~= name then
        local geometry = assetGeometry[name] or {}
        person:set { src = basePath .. name .. ".bin", x = geometry.x or 0, y = geometry.y or 0 }
        state.personSrc = name
    end
    -- Fully opaque source frames avoid a dark alpha gap during a pose change.
    opacity(person, 255)
    state.form = name == "bomb" and "bomb" or "human"
end
local function two(n) return n ~= nil and string.format("%02d", n) or "--" end
local function comma(n)
    if n == nil then return "--" end
    return string.format("%d", n):reverse():gsub("(%d%d%d)", "%1,"):reverse():gsub("^,", "")
end
local weekCN = { "周日", "周一", "周二", "周三", "周四", "周五", "周六" }
local weekEN = { "SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT" }
local function renderData()
    if not state.active then return end
    set(timeLabel, "text", two(values.hour) .. ":" .. two(values.minute))
    if values.month and values.day and values.week ~= nil then
        if chineseFonts[DATE_SIZE] then
            set(dateLabel, "text", string.format("%02d/%02d %s", values.month, values.day, weekCN[values.week + 1]))
        else
            set(dateLabel, "text", string.format("%02d/%02d %s", values.month, values.day, weekEN[values.week + 1]))
        end
    else set(dateLabel, "text", "--") end
    renderBattery()
    set(stepLabel, "text", comma(values.steps))
    set(heartLabel, "text", values.heart ~= nil and tostring(values.heart) or "--")
end

local function canRun() return state.active and not state.destroyed and not state.initializing and not state.resuming end
local function deleteTimer(slot)
    local timer = state[slot]
    state[slot] = nil
    if timer then timer:delete() end
end
local function clearEffects()
    opacity(fireworks1, 0); opacity(fireworks2, 0)
    opacity(smoke, 0); opacity(flash, 0)
    set(cover, "bg_opa", 0)
end
local function humanExpression(emotion, closed)
    state.emotion, state.closed = emotion, closed
    setPerson("human-" .. emotion .. (closed and "-closed" or "-open"))
end
local idleEvents = {
    { delay = 1200, emotion = "neutral", closed = true },
    { delay = 180, emotion = "neutral", closed = false },
    { delay = 4620, emotion = "smile", closed = false },
    { delay = 1200, emotion = "smile", closed = true },
    { delay = 180, emotion = "smile", closed = false },
    { delay = 420, emotion = "neutral", closed = false },
}
local function startIdle()
    if not canRun() or state.running or state.heldFlower or state.form ~= "human" or state.idleTimer then return end
    local epoch = state.epoch
    state.idleCursor = 1
    state.idleTimer = lvgl.Timer {
        period = idleEvents[1].delay,
        cb = function(timer)
            if not canRun() or state.epoch ~= epoch or state.idleTimer ~= timer or state.running or state.heldFlower then
                if state.idleTimer == timer then state.idleTimer = nil end
                timer:delete(); return
            end
            local event = idleEvents[state.idleCursor]
            humanExpression(event.emotion, event.closed)
            state.idleCursor = state.idleCursor % #idleEvents + 1
            timer:set { period = idleEvents[state.idleCursor].delay }
            timer:resume()
        end,
    }
    state.idleTimer:resume()
end
local function restoreHuman(reason)
    deleteTimer("transientTimer"); deleteTimer("idleTimer")
    state.epoch = state.epoch + 1
    state.running, state.elapsed, state.origin = false, 0, "idle"
    state.phase, state.heldFlower = "idle", false
    clearEffects()
    setBackdrop(false)
    humanExpression("neutral", false)
    record(reason or "human")
    startIdle()
end
local function smooth(from, to, t)
    local p = math.max(0, math.min(1, (t - from) / (to - from)))
    return p * p * (3 - 2 * p)
end
local function timeline(t)
    local phase
    if t < 400 then
        setPerson("human-neutral-open"); phase = "pull"
    elseif t < 450 then
        setPerson("pull-start"); phase = "pull"
    elseif t < 750 then
        setPerson("pull-1"); phase = "pull"
    elseif t < 800 then
        setPerson("pull-bridge"); phase = "pull"
    elseif t < 900 then
        setPerson("pull-mid"); phase = "pull"
    elseif t < 950 then
        setPerson("pull-finish"); phase = "pull"
    elseif t < 1900 then
        setPerson("pull-2"); phase = t < 1000 and "pull" or "blast"
    else
        -- The sole human-to-bomb source swap occurs behind two fully opaque layers.
        setPerson("bomb"); phase = t < 2900 and "blast" or (t < 6700 and "burst" or "bomb")
    end
    if state.phase ~= phase then state.phase = phase; record("phase-" .. phase) end
    local smokeOpacity = t < 1600 and 255 * smooth(1000, 1600, t)
        or (t < 2100 and 255 or 255 * (1 - smooth(2100, 2900, t)))
    opacity(smoke, smokeOpacity)
    set(cover, "bg_opa", math.floor(smokeOpacity + 0.5))
    local flashOpacity = t < 1450 and 255 * smooth(1000, 1450, t)
        or 255 * (1 - smooth(1450, 2400, t))
    opacity(flash, flashOpacity)
    opacity(fireworks1, 255 * smooth(3100, 3900, t) * (1 - smooth(3900, 5300, t)))
    opacity(fireworks2, 255 * smooth(3900, 5300, t))
end
local startTransient
startTransient = function()
    if not canRun() or not state.running or state.transientTimer then return end
    local epoch = state.epoch
    state.transientTimer = lvgl.Timer {
        period = 50,
        cb = function(timer)
            if not canRun() or state.epoch ~= epoch or state.transientTimer ~= timer or not state.running then
                if state.transientTimer == timer then state.transientTimer = nil end
                timer:delete(); return
            end
            state.elapsed = state.elapsed + 50
            timeline(math.min(state.elapsed, 6700))
            if state.elapsed >= 6700 then
                state.transientTimer = nil; timer:delete(); state.running = false
                if values.heart ~= nil and values.heart > HEART_RATE_THRESHOLD then record("complete-bomb")
                else restoreHuman("complete-human") end
            end
        end,
    }
    state.transientTimer:resume()
end
local function beginTransform()
    if not state.active or state.destroyed then return end
    deleteTimer("idleTimer"); deleteTimer("transientTimer")
    state.epoch = state.epoch + 1
    state.running, state.elapsed, state.origin = true, 0, "auto"
    state.closed, state.emotion, state.heldFlower = false, "neutral", false
    state.triggerCount = state.triggerCount + 1
    state.autoTriggerCount = state.autoTriggerCount + 1
    setBackdrop(true)
    clearEffects(); timeline(0); record("start-auto")
    startTransient()
end
local function heartChanged(value)
    if not state.active or state.destroyed then return end
    if value == nil then
        -- Unknown data never creates a threshold edge; retain the high-interval latch.
        if state.origin == "auto" and (state.running or state.form == "bomb") then
            restoreHuman("heart-unknown")
        end
    elseif value <= HEART_RATE_THRESHOLD then
        state.highLatched = false
        if state.running or state.form == "bomb" then restoreHuman("heart-low") end
    elseif not state.highLatched then
        state.highLatched = true
        record("heart-high")
        beginTransform()
    elseif not state.running and state.form == "human" then
        -- A missing sample may have temporarily restored the human. A valid
        -- high sample in the same interval restores the final form without
        -- replaying the explosion or creating a new threshold edge.
        deleteTimer("idleTimer")
        state.epoch = state.epoch + 1
        state.heldFlower, state.emotion, state.closed = false, "neutral", false
        state.elapsed, state.origin = 6700, "auto"
        setBackdrop(true); clearEffects(); timeline(6700)
        record("heart-high-restored")
    end
end
local touch = lvgl.Object(face, {
    x = 0, y = 0, w = 336, h = 480,
    bg_opa = 0, border_width = 0, pad_all = 0,
})
touch:clear_flag(lvgl.FLAG.SCROLLABLE)
touch:add_flag(lvgl.FLAG.CLICKABLE)
-- Bubble long-press events for the system watchface menu.
touch:add_flag(lvgl.FLAG.EVENT_BUBBLE)
touch:onClicked(function()
    if not canRun() or state.running or state.form ~= "human" or (values.heart and values.heart > HEART_RATE_THRESHOLD) then return end
    deleteTimer("idleTimer")
    state.epoch = state.epoch + 1
    state.heldFlower = not state.heldFlower
    state.emotion, state.closed = "neutral", false
    if state.heldFlower then setPerson("human-flower"); record("flower-show")
    else humanExpression("neutral", false); record("flower-hide"); startIdle() end
end)

-- The native dataman API delivers 24.8 fixed-point values. This reads the latest
-- available measurement; it does not request a heart sensor sample.
local function decode(encoded, maximum, minimum)
    if type(encoded) ~= "number" or encoded ~= encoded or encoded == math.huge or encoded == -math.huge
        or encoded == 2147483647 or encoded < 0 then return nil end
    local value = encoded // 256
    if value > maximum or value < (minimum or 0) then return nil end
    return value
end
local function subscribe(key, object, field, maximum, minimum)
    local ok, token = pcall(dataman.subscribe, key, object, function(_, encoded)
        if state.destroyed then return end
        values[field] = decode(encoded, maximum, minimum)
        if field == "heart" then heartChanged(values.heart) end
        renderData()
    end)
    if ok and token ~= nil then tokens[#tokens + 1] = token end
end
subscribe("timeHour", timeLabel, "hour", 23)
subscribe("timeMinute", timeLabel, "minute", 59)
subscribe("dateMonth", dateLabel, "month", 12, 1)
subscribe("dateDay", dateLabel, "day", 31, 1)
subscribe("dateWeek", dateLabel, "week", 6)
subscribe("systemStatusBattery", batteryBody, "battery", 100)
subscribe("healthStepCount", stepLabel, "steps", 999999)
subscribe("healthHeartRate", heartLabel, "heart", 999, 1)
local function pauseSubscriptions(paused)
    local operation = paused and dataman.pause or dataman.resume
    if type(operation) ~= "function" then return end
    for _, token in ipairs(tokens) do pcall(operation, token) end
end
local function pauseFace()
    if not state.active or state.destroyed then return end
    state.active = false
    deleteTimer("transientTimer"); deleteTimer("idleTimer")
    state.epoch = state.epoch + 1
    -- Keep transformation elapsed frozen. An idle human wakes with open eyes.
    if not state.running and state.form == "human" and not state.heldFlower then humanExpression("neutral", false) end
    pauseSubscriptions(true); record("screen-off")
end
local function resumeFace()
    if state.active or state.destroyed then return end
    state.active, state.resuming = true, true
    -- Resume can synchronously publish cached values; defer timer creation until
    -- all subscriptions have resumed and the latest HR has been reconciled.
    pauseSubscriptions(false)
    heartChanged(values.heart)
    state.resuming = false
    if state.running then timeline(math.min(state.elapsed, 6700)); startTransient()
    else startIdle() end
    renderData(); record("screen-on")
end
function ScreenStateChangedCB(previous, current, reason)
    if current == "ON" then resumeFace() else pauseFace() end
end
pageOnPause, pageOnResume = pauseFace, resumeFace
-- Some firmware builds expose explicit data cancellation, others release the
-- subscription with its LVGL object. Always pause first; optional cleanup is
-- guarded so unavailable unsubscribe interfaces cannot break teardown.
function onDestroy()
    if state.destroyed then return end
    state.active, state.destroyed = false, true
    state.epoch = state.epoch + 1
    deleteTimer("transientTimer"); deleteTimer("idleTimer")
    pauseSubscriptions(true)
    for _, token in ipairs(tokens) do
        if type(dataman.unsubscribe) == "function" then
            pcall(dataman.unsubscribe, token)
        else
            pcall(function()
                if type(token.unsubscribe) == "function" then token:unsubscribe() end
            end)
        end
    end
    tokens = {}
    record("destroy")
end
-- Read-only, bounded diagnostics for host-side verification. No simulated data
-- is injected into the watchface, and these fields are never shown on screen.
function RezeBombDebug()
    local events = {}
    for i, event in ipairs(state.log) do
        events[i] = { event = event.event, elapsed = event.elapsed, phase = event.phase }
    end
    return {
        active = state.active, destroyed = state.destroyed, phase = state.phase, form = state.form, elapsed = state.elapsed,
        running = state.running, origin = state.origin, highLatched = state.highLatched,
        triggerCount = state.triggerCount, autoTriggerCount = state.autoTriggerCount,
        manualTriggerCount = state.manualTriggerCount, heart = values.heart,
        personSrc = state.personSrc, backdrop = state.backdrop, heldFlower = state.heldFlower,
        emotion = state.emotion, closed = state.closed,
        transientTimerActive = state.transientTimer ~= nil, idleTimerActive = state.idleTimer ~= nil,
        tokenCount = #tokens, log = events,
    }
end
state.initializing = false
renderData()
if state.running then startTransient() else startIdle() end
record("ready")
