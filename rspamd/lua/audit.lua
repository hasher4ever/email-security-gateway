-- Lua rule: write every scanned mail's verdict + matched rules to the
-- mail_audit Postgres table. This is the visibility backbone — shadow mode
-- depends on this for tuning.

local rspamd_logger = require "rspamd_logger"
local rspamd_redis  = require "rspamd_redis"

local function gather_urls(task)
    local out = {}
    for _, u in ipairs(task:get_urls() or {}) do
        table.insert(out, u:get_text())
    end
    return out
end

local function gather_attachments(task)
    local out = {}
    for _, p in ipairs(task:get_parts() or {}) do
        if p:is_attachment() then
            table.insert(out, {
                filename = p:get_filename() or "",
                length   = p:get_length() or 0,
                ctype    = (p:get_mimepart() and p:get_mimepart():get_type()) or "",
            })
        end
    end
    return out
end

rspamd_config:register_symbol{
    name = "AUDIT_LOG",
    type = "postfilter",
    priority = 10,
    callback = function(task)
        local r       = task:get_metric_result()
        local score   = r and r.score or 0
        local action  = r and r.action or "no action"
        local symbols = {}
        for sym, _ in pairs(task:get_symbols_all() or {}) do
            table.insert(symbols, sym)
        end

        local sender = task:get_from("smtp")
        local sender_addr = (sender and sender[1] and sender[1].addr) or ""
        local sender_dom  = (sender and sender[1] and sender[1].domain) or ""

        rspamd_logger.infox(task,
            "AUDIT score=%s action=%s sender=%s symbols=%s urls=%s atts=%s",
            score, action, sender_addr,
            table.concat(symbols, ","),
            #gather_urls(task),
            #gather_attachments(task))

        -- TODO Phase 1.1: push the full audit row to Postgres via a sidecar
        -- worker (Lua's pg client in Rspamd is limited; easier to ship via
        -- Redis pub/sub to a Python consumer that writes to Postgres).
        return true
    end,
}
