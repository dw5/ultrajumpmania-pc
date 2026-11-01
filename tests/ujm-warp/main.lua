-- name: UJM Test Warp
-- description: Test only. Enters a level through the hub's own warp object, so the act select screen shows.

local LEVEL = 9
local warped = false
local timer = 0

hook_event(HOOK_UPDATE, function()
    if warped or gNetworkPlayers[0].currLevelNum ~= LEVEL_CASTLE_GROUNDS then return end
    timer = timer + 1
    if timer < 60 then return end
    warped = true
    local m = gMarioStates[0]
    for _, list in ipairs({ OBJ_LIST_LEVEL, OBJ_LIST_SURFACE, OBJ_LIST_GENACTOR }) do
        local o = obj_get_first(list)
        while o ~= nil do
            local node = area_get_warp_node_from_params(o)
            if node ~= nil then
                print("ujm-warp", get_behavior_name_from_id(get_id_from_behavior(o.behavior)), node.node.id, node.node.destLevel, node.node.destArea, node.node.destNode)
                if node.node.destLevel == LEVEL and m.usedObj ~= o then
                    m.usedObj = o
                    print("ujm-warp using it", level_trigger_warp(m, WARP_OP_WARP_OBJECT))
                    return
                end
            end
            o = obj_get_next(o)
        end
    end
    print("ujm-warp no warp object leads to level", LEVEL)
end)

-- Log every warp, to tell a level's own warp from one the port causes.
hook_event(HOOK_ON_WARP, function(warpType, level, area, node)
    print("ujm-warp warp", warpType, level, area, node, gMarioStates[0].action, gMarioStates[0].pos.x, gMarioStates[0].pos.y, gMarioStates[0].pos.z)
end)

-- Log action changes in the level, to see what leads to a death exit.
local lastAction = 0
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 and m.action ~= lastAction and gNetworkPlayers[0].currLevelNum == LEVEL then
        lastAction = m.action
        print("ujm-warp action", string.format("0x%x", m.action), m.health, m.pos.x, m.pos.y, m.pos.z, m.floor ~= nil and m.floor.type or -1)
    end
end)
