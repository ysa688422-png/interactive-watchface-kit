-- Execute the exact supplied source against independent LVGL/dataman host doubles.
-- Does not claim device, firmware, image rendering, Bluetooth or sensor validation.
local component = assert(arg[1], "pass native or extracted main.lua")
local stub = dofile("tests/lua/native_stub.lua")
local checks, scenarios = 0, 0
local function check(value, message)
    checks = checks + 1
    assert(value, message or ("check " .. checks))
end
local function eq(actual, expected, message)
    check(actual == expected, (message or "unexpected value") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
local function activeTimers(state)
    local n = 0
    for _, timer in ipairs(state.timers) do if not timer.deleted and not timer.paused then n = n + 1 end end
    return n
end
local function pictureName(src) return src and src:match("([^/]+)%.bin$") end
local function loadFace(options)
    options = options or {}
    local state = stub.new(options)
    if options.no_fonts then state.lvgl.Font = function() error("font unavailable") end end
    state:install()
    _G.pageOnPause, _G.pageOnResume, _G.onDestroy, _G.WatchfaceDebug = nil, nil, nil, nil
    assert(loadfile(component))()
    check(type(WatchfaceDebug) == "function", "read-only diagnostics exist")
    state.debug = WatchfaceDebug
    state.screen, state.pause, state.resume, state.destroy = ScreenStateChangedCB, pageOnPause, pageOnResume, onDestroy
    for _, callback in ipairs({state.screen, state.pause, state.resume, state.destroy}) do
        check(type(callback) == "function", "lifecycle callback exists")
    end
    state.touch = state:find(function(o) return o.clicked ~= nil end)[1]
    check(state.touch ~= nil, "touch target exists")
    check(state.touch.flags.EVENT_BUBBLE, "system long-press events can bubble")
    local targets = state.subscriptionTargets
    state.labels = {
        time = targets.timeHour, date = targets.dateMonth,
        steps = targets.healthStepCount,
        heart = targets.healthHeartRate,
    }
    for _, key in ipairs({"time", "date", "steps", "heart"}) do check(state.labels[key], "live " .. key .. " label exists") end
    eq(targets.timeHour, targets.timeMinute, "time fields share one semantic label")
    eq(targets.dateMonth, targets.dateDay, "date fields share one semantic label")
    eq(targets.dateMonth, targets.dateWeek, "weekday shares the date label")
    local function objectAt(x,y)
        return state:find(function(o) return o.kind == "Object" and o.props.x == x and o.props.y == y end)[1]
    end
    state.battery = {body = targets.systemStatusBattery,
        terminal = objectAt(310,34), fill = objectAt(283,33), unknown = objectAt(290,36)}
    for _,key in ipairs({"body","terminal","fill","unknown"}) do check(state.battery[key],"battery " .. key .. " exists") end
    eq(state.battery.body.kind,"Object","battery subscription targets graphical body")
    state.icons, state.layers, state.objectOrder = {}, {}, {}
    for index,o in ipairs(state.objects) do
        state.objectOrder[o] = index
        if o.kind == "Image" then
            local name=pictureName(o.props.src) or ""
            if name:match("^icon%-steps%-") then state.icons.steps=o end
            if name:match("^icon%-heart%-") then state.icons.heart=o end
            if name == "ui-background-shade" then state.layers.shade=o end
            if name == "fireworks-1" then state.layers.fireworks1=o end
            if name == "fireworks-2" then state.layers.fireworks2=o end
            if name == "smoke" then state.layers.smoke=o end
            if name == "flash" then state.layers.flash=o end
            if name == "footer-lavender" then state.layers.footer=o end
            if name == state.debug().personSrc then state.layers.person=o end
        elseif o.kind == "Object" and o.props.bg_color == 0x342C2A then
            state.layers.cover=o
        end
    end
    check(state.icons.steps,"step icon exists")
    check(state.icons.heart,"heart icon exists")
    check(state.layers.shade,"background-only readability shade exists")
    return state
end
local function effectiveOpacity(object)
    return (object.props.opa or 255) * (object.props.bg_opa or 255) / 255
end
local function batteryValue(state,width,filled,unknown)
    eq(state.battery.fill.props.w,width,"battery fill width")
    eq(effectiveOpacity(state.battery.fill),filled and 255 or 0,"battery fill visibility")
    eq(effectiveOpacity(state.battery.unknown),unknown and 255 or 0,"unknown battery dash visibility")
end
local function iconTheme(state,black)
    -- These suffixes identify background themes, not foreground ink colors.
    local suffix=black and "dark" or "light"
    local ink=black and 0xFFFFFF or 0x34233F
    eq(pictureName(state.icons.steps.props.src),"icon-steps-"..suffix,"step icon theme")
    eq(pictureName(state.icons.heart.props.src),"icon-heart-"..suffix,"heart icon theme")
    eq(state.layers.shade.props.opa,black and 255 or 0,"readability shade follows background theme")
    eq(state.battery.body.props.border_color,ink,"battery border color")
    for _,key in ipairs({"terminal","fill","unknown"}) do
        eq(state.battery[key].props.bg_color,ink,"battery " .. key .. " color")
    end
end
local function human(state, holding)
    local d = state.debug()
    eq(d.form, "human", "human form")
    eq(d.backdrop, "lavender", "human lavender background")
    eq(d.heldFlower, holding or false, "held flower")
    eq(d.running, false, "no transform running")
    if holding then eq(d.personSrc, "human-flower", "flower artwork visible") end
end
local function paused(state)
    eq(activeTimers(state), 0, "no active timers while asleep")
    eq(state.debug().active, false, "inactive while asleep")
    for _, token in ipairs(state.subscriptions) do check(token.paused, "subscription paused") end
    eq(state:advance(30000), 0, "sleep causes no timer callbacks")
end
local function finish(state)
    state.destroy()
    eq(activeTimers(state), 0, "scenario teardown stops timers")
    for _, token in ipairs(state.subscriptions) do check(token.paused, "scenario teardown pauses subscriptions") end
end
local function pass(name) scenarios = scenarios + 1; print("PASS " .. name) end

do
    local s = loadFace()
    eq(#s.subscriptions, 8, "eight separate real-data subscriptions")
    eq(s.labels.time.props.text, "--:--", "no invented clock")
    eq(s.labels.steps.props.text, "--", "no invented steps")
    eq(s.labels.heart.props.text, "--", "unknown HR displayed")
    human(s)
    eq(activeTimers(s), 1, "one idle expression timer")
    for key,value in pairs({timeHour=9,timeMinute=7,dateMonth=10,dateDay=19,dateWeek=1,
        systemStatusBattery=82,healthStepCount=6280,healthHeartRate=120}) do s:publish(key,value*256) end
    eq(s.labels.time.props.text, "09:07", "encoded live clock")
    eq(s.labels.date.props.text, "10/19 周一", "compact encoded live date")
    batteryValue(s,20,true,false)
    eq(s.labels.steps.props.text, "6,280", "encoded live steps")
    eq(s.labels.heart.props.text, "120", "120 displayed faithfully")
    s:advance(1200); eq(s.debug().closed, true, "automatic blink")
    s:advance(180); eq(s.debug().closed, false, "automatic eye reopening")
    s:advance(4620); eq(s.debug().emotion, "smile", "automatic smile")
    eq(s.debug().triggerCount, 0, "120 never triggers")
    s:publish("healthHeartRate", 121*256)
    eq(s.debug().triggerCount, 1, "121 starts once")
    eq(s.debug().autoTriggerCount, 1, "automatic trigger")
    eq(s.debug().backdrop, "black", "transformation uses black backdrop")
    eq(activeTimers(s), 1, "one transform timer replaces idle timer")
    s:advance(1900)
    eq(s.debug().personSrc, "bomb", "bomb revealed at covered swap")
    local cover = s:find(function(o) return o.kind == "Object" and o.props.bg_color == 0x342C2A end)[1]
    eq(cover.props.bg_opa, 255, "body swap fully covered")
    s:advance(4800)
    eq(s.debug().phase, "bomb", "completed bomb phase")
    eq(s.debug().running, false, "finite transformation")
    eq(activeTimers(s), 0, "completed high state does not animate forever")
    for _,hr in ipairs({121,130,155,121}) do s:publish("healthHeartRate",hr*256); s:advance(10000) end
    eq(s.debug().triggerCount, 1, "continuous high interval never restarts")
    s:click(s.touch)
    eq(s.debug().triggerCount, 1, "high click does not replay")
    eq(s.debug().manualTriggerCount, 0, "no manual transform injection")
    s:publish("healthHeartRate",120*256); human(s)
    eq(s.debug().highLatched, false, "120 clears threshold latch")
    s:publish("healthHeartRate",121*256)
    eq(s.debug().triggerCount, 2, "new low-to-high interval triggers once")
    finish(s); pass("real data, auto blink/smile, exact 120/121 edge, one-shot, covered swap and low restore")
end

do
    local s = loadFace()
    -- A nominal font_size alone cannot prove that the selected text_font is
    -- large. Confirm that the normal Font(name, size) path requested matching
    -- sizes. The host font object is a test double, not device glyph metrics.
    for name,expected in pairs({time=48,date=18,steps=32,heart=36}) do
        local props=s.labels[name].props
        eq(props.font_size,expected,"nominal " .. name .. " size")
        eq(type(props.text_font),"table","normal " .. name .. " uses constructed font")
        eq(props.text_font.size,expected,"selected " .. name .. " font size matches requested size")
        check(props.h >= expected,"normal " .. name .. " label has enough nominal font height")
    end
    for key,value in pairs({timeHour=23,timeMinute=59,dateMonth=12,dateDay=31,dateWeek=3,
        systemStatusBattery=100,healthStepCount=999999,healthHeartRate=999}) do s:publish(key,value*256) end
    eq(s.labels.time.props.text,"23:59","maximum clock string retained")
    eq(s.labels.date.props.text,"12/31 周三","compact maximum-width date retained")
    batteryValue(s,24,true,false)
    eq(s.labels.steps.props.text,"999,999","maximum steps retained without shortening")
    eq(s.labels.heart.props.text,"999","maximum valid HR retained")
    eq(s.debug().triggerCount,1,"large valid HR triggers normally")
    finish(s); pass("large font constructor sizes and longest supported live data strings")
end

do
    local s=loadFace()
    local body=s.battery.body.props
    eq(body.x,280,"battery body x"); eq(body.y,30,"battery body y")
    eq(body.w,30,"battery body width"); eq(body.h,14,"battery body height")
    eq(body.border_width,1,"battery fine outline width"); eq(body.radius,3,"battery rounded outline")
    eq(s.battery.terminal.props.w,2,"battery terminal width"); eq(s.battery.terminal.props.h,6,"battery terminal height")
    eq(s.battery.fill.props.h,8,"battery fill height"); eq(s.battery.fill.props.radius,1,"battery fill radius")
    eq(s.battery.unknown.props.w,10,"unknown dash width"); eq(s.battery.unknown.props.h,2,"unknown dash height")
    eq(s.icons.steps.props.x,89,"step icon x"); eq(s.icons.steps.props.y,455,"step icon y")
    eq(s.icons.heart.props.x,256,"heart icon x"); eq(s.icons.heart.props.y,455,"heart icon y")
    for _,icon in pairs(s.icons) do
        if icon.props.w ~= nil then eq(icon.props.w,22,"declared icon width") end
        if icon.props.h ~= nil then eq(icon.props.h,22,"declared icon height") end
    end
    local function noTextCaptions()
        local labels=s:find(function(o) return o.kind == "Label" end)
        eq(#labels,4,"only clock/date/steps/heart are textual labels")
        for _,o in ipairs(labels) do
            local value=o.props.text or ""
            check(value~="步数" and value~="心率" and value~="STEP" and value~="HR","text captions replaced by icons")
            check(not value:find("%",1,true),"battery has no percentage text")
        end
    end
    noTextCaptions(); iconTheme(s,false); batteryValue(s,1,false,true)
    for _,case in ipairs({{0,1,false},{1,1,true},{19,5,true},{20,5,true},{82,20,true},{100,24,true}}) do
        s:publish("systemStatusBattery",case[1]*256)
        batteryValue(s,case[2],case[3],false)
        noTextCaptions()
    end
    for _,invalid in ipairs({2147483647,-256,101*256,1000*256,0/0,math.huge,"82",{}}) do
        s:publish("systemStatusBattery",invalid)
        batteryValue(s,1,false,true)
    end
    s:publish("systemStatusBattery",nil); batteryValue(s,1,false,true)
    s:publish("healthHeartRate",121*256); iconTheme(s,true)
    batteryValue(s,1,false,true)
    s:publish("systemStatusBattery",82*256); batteryValue(s,20,true,false)
    s:publish("healthHeartRate",120*256); iconTheme(s,false)
    batteryValue(s,20,true,false); noTextCaptions()
    finish(s); pass("graphical battery limits/unknown, icon themes, geometry and removal of text captions")
end

do
    local s=loadFace()
    local layers,order=s.layers,s.objectOrder
    for _,name in ipairs({"fireworks1","fireworks2","shade","person","cover","smoke","flash","footer"}) do
        check(layers[name],"required scene layer exists: " .. name)
        eq(layers[name].parent,layers.person.parent,"scene layers share parent: " .. name)
    end
    check(order[layers.fireworks1] < order[layers.shade],"shade above first background fireworks")
    check(order[layers.fireworks2] < order[layers.shade],"shade above second background fireworks")
    for _,name in ipairs({"person","cover","smoke","flash","footer"}) do
        check(order[layers.shade] < order[layers[name]],"shade cannot cover foreground " .. name)
    end
    check(order[layers.person] < order[layers.cover],"smoke cover stays above character")
    check(order[layers.cover] < order[layers.smoke],"smoke image stays above opaque cover")
    check(order[layers.smoke] < order[layers.flash],"explosion flash stays above smoke")
    check(order[layers.flash] < order[layers.footer],"footer stays above transient effects")
    check(order[layers.footer] < order[s.labels.time],"live UI is above effect stack")
    local obsolete=s:find(function(o)
        return o.kind == "Object" and o.parent == layers.person.parent and
            ((o.props.x == 8 and o.props.y == 8) or (o.props.x == 246 and o.props.y == 14))
    end)
    eq(#obsolete,0,"old top-of-art clock/battery backplates removed")
    eq(layers.shade.props.opa,0,"no background shade in initial lavender theme")
    eq(layers.shade.props.x,0,"shade starts at canvas left")
    eq(layers.shade.props.y,0,"shade starts at canvas top")
    if layers.shade.props.w ~= nil then eq(layers.shade.props.w,336,"declared shade width") end
    if layers.shade.props.h ~= nil then eq(layers.shade.props.h,144,"declared shade height") end
    s:publish("healthHeartRate",121*256)
    eq(layers.shade.props.opa,255,"black theme enables background shade")
    s:advance(1900)
    eq(s.debug().personSrc,"bomb","covered bomb swap preserved")
    eq(layers.cover.props.bg_opa,255,"foreground explosion cover remains fully opaque")
    check(order[layers.shade] < order[layers.person],"same character widget remains above shade after swap")
    s:advance(4800)
    eq(layers.shade.props.opa,255,"completed fireworks retain only background readability shade")
    s:publish("healthHeartRate",120*256)
    eq(layers.shade.props.opa,0,"returning human clears background shade")
    finish(s); pass("background-only shade ordering, theme opacity and absence of foreground backplates")
end

do
    local s = loadFace({initial_values={healthHeartRate=81*256}})
    s:advance(1200)
    eq(s.debug().closed,true,"started in blink")
    s:click(s.touch); human(s,true)
    eq(activeTimers(s),0,"holding flower stops face timer")
    eq(s:advance(30000),0,"flower remains one still picture")
    s:click(s.touch); human(s)
    eq(s.debug().personSrc,"human-neutral-open","second click restores open eyes")
    eq(activeTimers(s),1,"returning from flower restarts one idle timer")
    s:click(s.touch); human(s,true)
    s.pause(); paused(s); s.resume(); human(s,true)
    eq(activeTimers(s),0,"wake preserves still flower without a face timer")
    s:publish("healthHeartRate",121*256)
    eq(s.debug().heldFlower,false,"high HR clears flower")
    eq(s.debug().running,true,"high HR starts from human state")
    local elapsed=s.debug().elapsed
    s:click(s.touch)
    eq(s.debug().elapsed,elapsed,"high click does not reset elapsed")
    eq(s.debug().triggerCount,1,"high click does not trigger twice")
    finish(s); pass("click flower toggle, no facial overlay, held-flower sleep, high clears flower without manual replay")
end

do
    local s = loadFace()
    local invalid={2147483647,-256,0/0,math.huge,-math.huge,"121",{},0,1000*256}
    for _,v in ipairs(invalid) do
        s:publish("healthHeartRate",v)
        eq(s.debug().heart,nil,"invalid HR decoded to unknown")
        eq(s.labels.heart.props.text,"--","invalid HR shows --")
        eq(s.debug().triggerCount,0,"invalid HR does not transform")
    end
    s:publish("healthHeartRate",nil)
    eq(s.debug().triggerCount,0,"nil HR does not transform")
    s:publish("healthHeartRate",120*256+255)
    eq(s.debug().triggerCount,0,"fixed-point fractional value below 121 does not trigger")
    s:publish("healthHeartRate",121*256); s:advance(750)
    s:publish("healthHeartRate",2147483647); human(s)
    eq(s.debug().highLatched,true,"unknown does not invent a low interval")
    s:publish("healthHeartRate",135*256)
    eq(s.debug().triggerCount,1,"unknown-to-high does not replay latched interval")
    eq(s.debug().form,"bomb","return of valid latched high restores final bomb form")
    eq(s.debug().backdrop,"black","restored high state uses black backdrop")
    eq(activeTimers(s),0,"restored latched high does not start another animation timer")
    s:publish("healthHeartRate",120*256); s:publish("healthHeartRate",121*256)
    eq(s.debug().triggerCount,2,"valid low rearms after unknown")
    finish(s); pass("invalid/unknown HR and high-interval latch")
end

do
    local s = loadFace({initial_values={healthHeartRate=135*256,timeHour=23*256,timeMinute=59*256}})
    eq(s.debug().triggerCount,1,"synchronous startup high triggers once")
    eq(activeTimers(s),1,"startup creates exactly one timer after initialization")
    eq(s.labels.time.props.text,"23:59","synchronous startup clock")
    s:advance(6700); eq(s.debug().form,"bomb","startup high completes")
    finish(s); pass("synchronous cached high-HR initialization")
end

do
    local s = loadFace({replay_on_resume=true,initial_values={healthHeartRate=121*256}})
    s:advance(1250)
    local elapsed=s.debug().elapsed
    s.screen("ON","OFF","TEST"); s.pause(); paused(s)
    eq(s.debug().elapsed,elapsed,"sleep freezes animation time")
    s:publish("healthHeartRate",132*256)
    s.screen("OFF","ON","TEST"); s.resume()
    eq(s.debug().triggerCount,1,"cached high on resume does not retrigger")
    eq(s.debug().elapsed,elapsed,"resume keeps saved animation progress")
    eq(activeTimers(s),1,"duplicate resume creates one timer")
    s:advance(50); eq(s.debug().elapsed,elapsed+50,"animation continues after wake")
    s.pause(); s:publish("healthHeartRate",119*256); paused(s); s.resume()
    human(s)
    eq(s.labels.heart.props.text,"119","latest cached low applied on wake")
    eq(activeTimers(s),1,"cached low resumes idle only")
    s.pause(); s:publish("healthHeartRate",121*256); paused(s)
    eq(s.debug().triggerCount,1,"asleep high causes no eager trigger")
    s.resume(); eq(s.debug().triggerCount,2,"cached low-to-high starts once on wake")
    s.pause(); s:publish("healthHeartRate",2147483647); paused(s); s.resume()
    human(s)
    eq(s.labels.heart.props.text,"--","unknown cached HR applied on wake")
    eq(s.debug().highLatched,true,"unknown cached HR retains interval latch")
    eq(s.debug().triggerCount,2,"unknown cached HR cannot create another trigger")
    finish(s); pass("screen/page pause, no sleep work, latest cached low/high and idempotent wake")
end

do
    local s=loadFace({no_pause_resume=true})
    s:publish("healthHeartRate",81*256)
    s.pause(); eq(activeTimers(s),0,"missing optional data pause still stops animation")
    s:publish("healthHeartRate",121*256)
    eq(s.debug().triggerCount,0,"off-screen callback does not trigger")
    eq(s.labels.heart.props.text,"81","off-screen callback does not render")
    eq(s:advance(30000),0,"optional API absence causes no sleep work")
    s.resume(); eq(s.debug().triggerCount,1,"wake reconciles cached high without optional resume API")
    finish(s); pass("optional dataman pause/resume absence")
end

do
    local s=loadFace({initial_values={healthHeartRate=121*256}})
    s:advance(1700)
    local lastTimer=s.timers[#s.timers]
    local before=s.debug()
    s.destroy(); s.destroy()
    eq(s.debug().destroyed,true,"destroy state")
    eq(s.debug().active,false,"destroy deactivates")
    eq(s.debug().tokenCount,0,"destroy clears owned token references")
    eq(s.unsubscribeCalls,8,"destroy unsubscribes each token once")
    eq(activeTimers(s),0,"destroy removes all timers")
    for _,sub in ipairs(s.subscriptions) do
        check(sub.paused and sub.unsubscribed,"subscription stopped and removed")
        sub.cb(sub.obj,80*256) -- A late queued callback must be harmless.
    end
    lastTimer.cb(lastTimer)
    s.resume(); s.screen("OFF","ON","TEST"); s:click(s.touch)
    eq(s.debug().heart,before.heart,"late data ignored after destroy")
    eq(s.debug().elapsed,before.elapsed,"late timer ignored after destroy")
    eq(s.debug().triggerCount,before.triggerCount,"destroy cannot restart")
    eq(s:advance(30000),0,"destroy causes no future timer callbacks")
    pass("destroy, repeated destroy, subscription disposal and stale callbacks")
    local fallback=loadFace({no_unsubscribe=true})
    fallback.destroy(); eq(fallback.debug().tokenCount,0,"fallback destroy drops token references")
    for _,sub in ipairs(fallback.subscriptions) do check(sub.paused,"fallback destroy always pauses tokens") end
    eq(activeTimers(fallback),0,"fallback destroy stops timers")
    pass("destroy fallback when unsubscribe is unavailable")
end

do
    local s=loadFace({no_fonts=true,reject_keys={healthHeartRate=true}})
    eq(#s.subscriptions,7,"unsupported HR key is isolated")
    s:publish("timeHour",9*256); s:publish("timeMinute",7*256)
    s:publish("dateMonth",10*256); s:publish("dateDay",19*256); s:publish("dateWeek",1*256)
    eq(s.labels.time.props.text,"09:07","other subscriptions survive missing HR")
    eq(s.labels.date.props.text,"10/19 MON","fallback date avoids Chinese glyph dependency")
    s:click(s.touch); human(s,true)
    eq(s.labels.heart.props.text,"--","unsupported HR remains unknown")
    finish(s); pass("missing optional HR subscription and font fallback")
end

do
    local s=loadFace()
    local objectCount=#s.objects
    for _=1,30 do
        s:publish("healthHeartRate",80*256)
        s:click(s.touch); s:click(s.touch)
        s:publish("healthHeartRate",121*256); s:advance(75)
        s:publish("healthHeartRate",90*256)
        check(activeTimers(s)<=1,"rapid interactions retain at most one timer")
    end
    eq(#s.objects,objectCount,"rapid interactions reuse all widgets")
    eq(s.debug().autoTriggerCount,30,"exactly one auto start per low/high interval")
    eq(s.debug().manualTriggerCount,0,"clicks never simulate health triggers")
    finish(s); pass("rapid flower/threshold interactions do not retain timers or widgets")
end

print("TOTAL " .. checks .. " assertions in " .. scenarios .. " scenarios; exact supplied Lua executed with host doubles; no hardware validation")
