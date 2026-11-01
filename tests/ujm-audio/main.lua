-- name: UJM audio log
-- description: Test only. Logs the level sequence player's volume state.
local t = 0
hook_event(HOOK_UPDATE, function()
    t = t + 1
    if t % 300 == 0 then
        print(string.format("AUDIO level %d seq %d fade %.3f vol %.3f mute %.3f tempo %d", gNetworkPlayers[0].currLevelNum, get_current_background_music(), sequence_player_get_fade_volume(0), sequence_player_get_volume(0), sequence_player_get_mute_volume_scale(0), sequence_player_get_tempo(0)))
    end
end)
-- A sleeping player lowers the music, so stay awake.
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 and m.action == ACT_IDLE and t % 200 == 0 then set_mario_action(m, ACT_IDLE, 0) end
end)
