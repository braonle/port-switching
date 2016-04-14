CREATE TABLE routers (extern_ip TEXT PRIMARY KEY, name TEXT);
CREATE TABLE switching (extern_port INTEGER, intern_ip TEXT, intern_port INTEGER);