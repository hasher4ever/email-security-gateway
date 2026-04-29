-- Lua rule: hand unknown URLs to the detonator service for sandbox analysis.
-- Phase 1 leaves this stubbed (returns 0); Phase 2 wires HTTP to the
-- detonator container.

local rspamd_http = require "rspamd_http"
local rspamd_logger = require "rspamd_logger"

local DETONATOR_URL = os.getenv("DETONATOR_URL") or "http://detonator:7000"
local TIMEOUT = tonumber(os.getenv("DETONATOR_TIMEOUT_SEC") or "30")

local function should_detonate(url)
    -- Skip if URL already matched a known-bad list (other rules fired with
    -- high score). Detonation budget is precious; only spend it on unknowns.
    if not url then return false end
    local tld = url:get_tld() or ""
    -- Skip well-known benign hosts
    local skip = { ["google.com"]=true, ["microsoft.com"]=true,
                   ["github.com"]=true, ["gov"]=true }
    return not skip[tld]
end

rspamd_config.URL_DETONATION = {
    callback = function(task)
        local urls = task:get_urls() or {}
        if #urls == 0 then return false end

        local found_phish = false
        for _, u in ipairs(urls) do
            if should_detonate(u) then
                local target = u:get_text()
                -- Phase 1: log only. Phase 2 enables the HTTP call.
                rspamd_logger.infox(task, "would detonate %s", target)
                -- local err, response = rspamd_http.request({
                --     task = task,
                --     url = DETONATOR_URL .. "/scan",
                --     method = "POST",
                --     body = '{"url":"' .. target .. '"}',
                --     timeout = TIMEOUT,
                --     headers = {["Content-Type"]="application/json"},
                -- })
                -- if not err and response and response.code == 200 then
                --     local ok, body = pcall(require("rspamd_util").parse_json, response.content)
                --     if ok and body.verdict == "phishing" then
                --         found_phish = true
                --     end
                -- end
            end
        end

        if found_phish then
            task:insert_result("DETONATED_PHISH", 14.0)
            return true
        end
        return false
    end,
    description = "Headless-Chrome detonation verdict (Phase 2)",
    score = 14.0,
    group = "phishing",
}
