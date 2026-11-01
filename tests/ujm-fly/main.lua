-- name: UJM Fly Log
-- description: Test only. Logs the distance between the player and the camera while free flying.
local t = 0
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or m.action ~= ACT_DEBUG_FREE_MOVE then return end
    t = t + 1
    if t % 15 == 0 then
        local p = gLakituState.pos
        print(string.format("FLY %d dist %.0f pos %.0f %.0f %.0f", t, math.sqrt((p.x - m.pos.x) ^ 2 + (p.y - m.pos.y) ^ 2 + (p.z - m.pos.z) ^ 2), m.pos.x, m.pos.y, m.pos.z))
    end
end)
