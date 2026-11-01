-- name: UJM Wall Scan
-- description: Test only. Counts how many walls the player's wall checks hit, standing or jumping above every floor.
local LEVEL = 16
local AREA = 1
-- The player's steps, then its ledge, swim, pole and punch checks, then typical object sizes.
local CHECKS = { {30, 24}, {60, 50}, {150, 50}, {30, 50}, {-10, 10}, {10, 110}, {50, 50}, {80, 5}, {10, 40}, {30, 60}, {50, 100}, {75, 150} }
local perCheck = {}
local BOUND, STEP, PER_FRAME = 16000, 64, 1000
local x, z = -BOUND, -BOUND
local wait, done, samples, over, worst = 0, false, 0, 0, 0
local counts = {}

local function query(px, py, pz, offset, radius)
    local d = collision_get_temp_wall_collision_data()
    d.x, d.y, d.z, d.offsetY, d.radius = px, py, pz, offset, radius
    find_wall_collisions(d)
    return d.numWalls
end

-- Walks towards a spot from all sides, pushed out by walls as the game does, ignoring floors so it can only overestimate.
local spots = {}
local function walk_in()
    local most, reached = 0, 0
    for _, s in ipairs(spots) do
        for dir = 0, 15 do
            for _, step in ipairs({ 4, 8, 12, 16, 25, 40 }) do
                local a = dir * math.pi / 8
                local px, pz = s[1] + math.cos(a) * 300, s[3] + math.sin(a) * 300
                for _ = 1, 300 / step + 20 do
                    local dx, dz = s[1] - px, s[3] - pz
                    local dist = math.sqrt(dx * dx + dz * dz)
                    if dist < step then break end
                    px, pz = px + dx / dist * step, pz + dz / dist * step
                    local d = collision_get_temp_wall_collision_data()
                    d.x, d.y, d.z, d.offsetY, d.radius = px, s[2], pz, s[4], s[5]
                    find_wall_collisions(d)
                    if d.numWalls > most then most = d.numWalls end
                    if d.numWalls > 4 then reached = reached + 1 end
                    px, pz = d.x, d.z
                end
            end
        end
    end
    print(string.format("WALK spots %d most walls %d steps over four %d", #spots, most, reached))
end

local function column(cx, cz)
    local y = 12000
    for _ = 1, 12 do
        local f = find_floor_height(cx, y, cz)
        if f <= -11000 then return end
        for lift = 0, 300, 100 do
            for _, c in ipairs(CHECKS) do
                local n = query(cx, f + lift, cz, c[1], c[2])
                samples = samples + 1
                counts[n] = (counts[n] or 0) + 1
                if n > 4 then
                    over = over + 1
                    if #spots < 200 then spots[#spots + 1] = { cx, f + lift, cz, c[1], c[2] } end
                    local key = c[1] .. "/" .. c[2]
                    perCheck[key] = (perCheck[key] or 0) + 1
                    if n > worst then
                        worst = n
                        print(string.format("WORST %d at %d %.0f %d lift %d offset %d radius %d", n, cx, f, cz, lift, c[1], c[2]))
                    end
                end
            end
        end
        y = f - 100
    end
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or done or gNetworkPlayers[0].currLevelNum ~= LEVEL or m.action == ACT_UNINITIALIZED then return end
    if gNetworkPlayers[0].currAreaIndex ~= AREA then
        wait = wait + 1
        if wait == 60 then warp_to_level(LEVEL, AREA, 1); wait = 0 end
        return
    end
    wait = wait + 1
    if wait < 60 then return end
    for _ = 1, PER_FRAME do
        column(x, z)
        z = z + STEP
        if z > BOUND then
            z = -BOUND
            x = x + STEP
            if x > BOUND then
                done = true
                local s = ""
                for k = 0, 40 do
                    if counts[k] then s = s .. string.format(" %d:%d", k, counts[k]) end
                end
                print(string.format("SCAN level %d area %d samples %d over4 %d worst %d hist%s", LEVEL, AREA, samples, over, worst, s))
                for k, v in pairs(perCheck) do print("CHECK", k, v) end
                walk_in()
                print("SCANDONE")
                return
            end
        end
    end
end)
