CREATE TABLE routers (extern_ip TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE switching (extern_port INTEGER PRIMARY KEY, intern_ip TEXT NOT NULL,
    intern_port INTEGER NOT NULL, UNIQUE(intern_ip, intern_port));