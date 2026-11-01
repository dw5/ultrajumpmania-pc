-- name: UJM Controls
-- description: Shows the default keyboard controls while paused.

local CONTROLS = {
    "Move: W A S D",
    "Jump (A): L",
    "Punch (B): ,",
    "Crouch (Z): K",
    "Pause (Start): Space",
    "Camera: Arrow keys",
    "Free fly on/off: Left Shift",
    "  Up: L  Down: K  Slow: ,",
}

local function on_hud_render()
    if not is_game_paused() then return end

    djui_hud_set_resolution(RESOLUTION_DJUI)
    djui_hud_set_font(FONT_NORMAL)
    local scale = 1
    local line = 32
    local x = 24
    local y = djui_hud_get_screen_height() - (#CONTROLS * line) - 24

    djui_hud_set_color(0, 0, 0, 170)
    djui_hud_render_rect(x - 12, y - 12, 300, #CONTROLS * line + 24)
    djui_hud_set_color(255, 255, 255, 255)
    for i, text in ipairs(CONTROLS) do
        djui_hud_print_text(text, x, y + (i - 1) * line, scale)
    end
end

hook_event(HOOK_ON_HUD_RENDER, on_hud_render)
