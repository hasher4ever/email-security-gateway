-- Lua rule: hand unknown URLs to the detonator service for sandbox analysis.

local rspamd_http = require "rspamd_http"
local rspamd_logger = require "rspamd_logger"
local rspamd_util = require "rspamd_util"

local DETONATOR_URL = os.getenv("DETONATOR_URL") or "http://detonator:7000"
local TIMEOUT = tonumber(os.getenv("DETONATOR_TIMEOUT_SEC") or "30")

local function should_detonate(url)
    -- Detonation budget is precious; only spend it on unknowns.
    if not url then return false end
    local tld = url:get_tld() or ""
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
                local body = rspamd_util.encode_json({ url = target })
                local err, response = rspamd_http.request({
                    task = task,
                    url = DETONATOR_URL .. "/scan",
                    method = "POST",
                    body = body,
                    timeout = TIMEOUT,
                    headers = {["Content-Type"]="application/json"},
                })
                if not err and response and response.code == 200 then
                    local ok, parsed = pcall(rspamd_util.parse_json, response.content)
                    if ok and parsed and parsed.verdict == "phishing" then
                        found_phish = true
                    end
                else
                    rspamd_logger.infox(task, "detonator call failed for %s: %s", target, err)
                end
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
