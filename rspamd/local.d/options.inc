# Rspamd global options
filters = "chartable,dkim,spf,surbl,regexp,fuzzy_check";
dns {
    nameserver = ["1.1.1.1", "8.8.8.8"];
    timeout = 1s;
    sockets = 16;
    retransmits = 5;
}
