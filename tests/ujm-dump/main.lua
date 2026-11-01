-- name: UJM Dump
-- description: Test only. Logs the player and every object some time after a level loads.
local t = 0
local level = -1
local AREA = 0
local LISTS = { OBJ_LIST_PLAYER, OBJ_LIST_EXT, OBJ_LIST_DESTRUCTIVE, OBJ_LIST_GENACTOR, OBJ_LIST_PUSHABLE, OBJ_LIST_LEVEL, OBJ_LIST_DEFAULT, OBJ_LIST_SURFACE, OBJ_LIST_POLELIKE, OBJ_LIST_SPAWNER, OBJ_LIST_UNIMPORTANT }

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or m.action == ACT_UNINITIALIZED then return end
    local n = gNetworkPlayers[0].currLevelNum
    local key = n * 10 + gNetworkPlayers[0].currAreaIndex
    if key ~= level then level = key; t = 0 end
    t = t + 1
    if AREA ~= 0 and n ~= LEVEL_CASTLE_GROUNDS and gNetworkPlayers[0].currAreaIndex ~= AREA then
        if t == 60 then warp_to_level(n, AREA, 1) end
        return
    end
    if t ~= 300 then return end
    print(string.format("DUMP M %d %d %x %.1f %.1f %.1f %d", n, gNetworkPlayers[0].currAreaIndex, m.action, m.pos.x, m.pos.y, m.pos.z, m.health))
    for _, list in ipairs(LISTS) do
        local o = obj_get_first(list)
        while o ~= nil do
            print(string.format("DUMP O %s %.1f %.1f %.1f %x", get_behavior_name_from_id(get_id_from_behavior(o.behavior)), o.oPosX, o.oPosY, o.oPosZ, o.oBehParams))
            o = obj_get_next(o)
        end
    end
    print("DUMP END")
end)
