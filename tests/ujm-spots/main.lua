-- name: UJM Spots
-- description: Test only. Teleports the player through UJM_SPOTS in spots.lua, for screenshots.
local SPOTS = {}
local i, t = 0, 0
local LEVEL = 16
local AREA = 0
local STEP = 0
local WARP6 = false
local areaWait = 0
local FREEZE = {}
local last = 0
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 and m.action ~= last then
        last = m.action
        print(string.format("END level %d area %d action %x pos %.0f %.0f %.0f stars %d", gNetworkPlayers[0].currLevelNum, gNetworkPlayers[0].currAreaIndex, m.action, m.pos.x, m.pos.y, m.pos.z, m.numStars))
    end
    if m.playerIndex ~= 0 or gNetworkPlayers[0].currLevelNum ~= LEVEL or m.action == ACT_UNINITIALIZED then return end
    if AREA ~= 0 and gNetworkPlayers[0].currAreaIndex ~= AREA then
        areaWait = areaWait + 1
        if areaWait == 60 then warp_to_level(LEVEL, AREA, 1); areaWait = 0 end
        return
    end
    t = t + 1
    if t == 1 then
        local o = obj_get_first_with_behavior_id(id_RM_Scroll_Texture)
        while o ~= nil do
            local n = obj_get_next_with_same_behavior_id(o)
            for _, p in ipairs(FREEZE) do
                if o.oBehParams == p then obj_mark_for_deletion(o) end
            end
            o = n
        end
    end
    if t % 200 == 0 then
        print(string.format("CAM %d yaw %d focus %.0f %.0f %.0f pos %.0f %.0f %.0f", gNetworkPlayers[0].currAreaIndex, m.faceAngle.y, gLakituState.curFocus.x, gLakituState.curFocus.y, gLakituState.curFocus.z, gLakituState.curPos.x, gLakituState.curPos.y, gLakituState.curPos.z))
    end
    if STEP > 0 and t > 400 and t < 1300 and (t - 400) % STEP == 0 then t = 399 end
    if t == 400 then
        i = i + 1
        local s = SPOTS[i]
        if s == nil then return end
        local y = find_floor_height(s[1], s[2], s[3])
        if y < s[2] - 1000 or s[5] then y = s[2] end
        m.pos.x, m.pos.y, m.pos.z = s[1], y, s[3]
        m.vel.x, m.vel.y, m.vel.z, m.forwardVel = 0, 0, 0, 0
        m.faceAngle.y = s[4] or 0
        m.health = 0x880
        set_mario_action(m, ACT_IDLE, 0)
        print(string.format("SPOT %d %.0f %.0f %.0f %d", i, m.pos.x, y, m.pos.z, m.faceAngle.y))
    end
    if t == 1400 then
        t = 0
        warp_restart_level()
    end
end)

-- Log every level change and warp request, including levels that have no player update.
local lastLevel = -1
hook_event(HOOK_UPDATE, function()
    if gNetworkPlayers[0].currLevelNum ~= lastLevel then
        lastLevel = gNetworkPlayers[0].currLevelNum
        print("LEVEL", lastLevel, gCurrLevelNum)
    end
end)
hook_event(HOOK_BEFORE_WARP, function(level, area, node, arg)
    print("BEFORE_WARP", level, area, node, arg)
    if WARP6 and level == 25 then return { destLevel = 6, destArea = 1, destWarpNode = 50 } end
end)
